from typing import Any, Dict, List, Optional, Tuple
from app.models.diff_result import Change, ChangeSeverity, ChangeType, DiffResult

def resolve_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    """Resolves a local JSON reference (e.g., '#/components/schemas/Model')."""
    if not ref.startswith('#/'):
        return {}
    parts = ref[2:].split('/')
    curr = spec
    for part in parts:
        if part in curr:
            curr = curr[part]
        else:
            return {}
    return curr

def get_schema(spec: Dict[str, Any], schema_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Returns the resolved schema if it's a reference, else returns the object itself."""
    if '$ref' in schema_obj:
        return resolve_ref(spec, schema_obj['$ref'])
    return schema_obj

def compare_schemas(
    old_spec: Dict[str, Any], 
    new_spec: Dict[str, Any], 
    old_schema: Dict[str, Any], 
    new_schema: Dict[str, Any], 
    path_prefix: str
) -> List[Change]:
    changes = []
    
    old_resolved = get_schema(old_spec, old_schema)
    new_resolved = get_schema(new_spec, new_schema)
    
    # Compare types
    old_type = old_resolved.get('type')
    new_type = new_resolved.get('type')
    if old_type and new_type and old_type != new_type:
        changes.append(Change(
            type=ChangeType.type_changed,
            severity=ChangeSeverity.BREAKING,
            path=path_prefix,
            description=f"Type changed from {old_type} to {new_type}",
            metadata={"old_type": old_type, "new_type": new_type}
        ))
        return changes # If type changed completely, don't dive deeper
        
    if old_type == 'object' or new_type == 'object' or 'properties' in old_resolved or 'properties' in new_resolved:
        old_props = old_resolved.get('properties', {})
        new_props = new_resolved.get('properties', {})
        old_required = set(old_resolved.get('required', []))
        new_required = set(new_resolved.get('required', []))
        
        removed_props = []
        added_props = []
        
        for prop_name, prop_schema in old_props.items():
            prop_path = f"{path_prefix}.properties.{prop_name}"
            if prop_name not in new_props:
                removed_props.append((prop_name, prop_schema, prop_path))
            else:
                # Recursively compare property schemas
                changes.extend(compare_schemas(
                    old_spec, new_spec, prop_schema, new_props[prop_name], prop_path
                ))
                
                # Check required status change
                is_old_req = prop_name in old_required
                is_new_req = prop_name in new_required
                if not is_old_req and is_new_req:
                    changes.append(Change(
                        type=ChangeType.required_status_changed,
                        severity=ChangeSeverity.BREAKING,
                        path=prop_path,
                        description=f"Property {prop_name} became required",
                        metadata={"prop_name": prop_name}
                    ))
        
        for prop_name, prop_schema in new_props.items():
            if prop_name not in old_props:
                prop_path = f"{path_prefix}.properties.{prop_name}"
                added_props.append((prop_name, prop_schema, prop_path))
                    
        # Probable rename heuristic
        if removed_props and added_props:
            # Simple heuristic: if there's exactly 1 removed and 1 added with same type
            for r_name, r_schema, r_path in list(removed_props):
                r_resolved = get_schema(old_spec, r_schema)
                r_type = r_resolved.get('type')
                
                candidate_matches = []
                for a_name, a_schema, a_path in added_props:
                    a_resolved = get_schema(new_spec, a_schema)
                    a_type = a_resolved.get('type')
                    if r_type and a_type and r_type == a_type:
                        candidate_matches.append((a_name, a_schema, a_path))
                
                if len(candidate_matches) == 1:
                    a_name, a_schema, a_path = candidate_matches[0]
                    changes.append(Change(
                        type=ChangeType.probable_rename,
                        severity=ChangeSeverity.WARNING,
                        path=path_prefix, # Use parent path for the rename
                        description=f"Property {r_name} was probably renamed to {a_name}",
                        confidence=0.8,
                        metadata={"old_name": r_name, "new_name": a_name}
                    ))
                    removed_props.remove((r_name, r_schema, r_path))
                    added_props.remove((a_name, a_schema, a_path))
                    
        # Report remaining added properties
        for a_name, a_schema, a_path in added_props:
            is_new_req = a_name in new_required
            if is_new_req:
                changes.append(Change(
                    type=ChangeType.required_field_added,
                    severity=ChangeSeverity.BREAKING,
                    path=a_path,
                    description=f"Required property {a_name} was added",
                    metadata={"prop_name": a_name}
                ))
            else:
                changes.append(Change(
                    type=ChangeType.field_added,
                    severity=ChangeSeverity.INFO,
                    path=a_path,
                    description=f"Optional property {a_name} was added",
                    metadata={"prop_name": a_name}
                ))

        # Report remaining removed properties
        for r_name, r_schema, r_path in removed_props:
            changes.append(Change(
                type=ChangeType.field_removed,
                severity=ChangeSeverity.BREAKING,
                path=r_path,
                description=f"Property {r_name} was removed",
                metadata={"prop_name": r_name}
            ))

    return changes

def compare_openapi_specs(old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> DiffResult:
    changes: List[Change] = []
    
    old_paths = old_spec.get('paths', {})
    new_paths = new_spec.get('paths', {})
    
    for path, new_methods in new_paths.items():
        if path not in old_paths:
            changes.append(Change(
                type=ChangeType.endpoint_added,
                severity=ChangeSeverity.INFO,
                path=path,
                description=f"Endpoint {path} was added"
            ))
        else:
            old_methods = old_paths[path]
            for method in new_methods:
                if method not in old_methods:
                    changes.append(Change(
                        type=ChangeType.method_added,
                        severity=ChangeSeverity.INFO,
                        path=f"{path}.{method.upper()}",
                        description=f"HTTP method {method.upper()} added for {path}"
                    ))
                    
    for path, old_methods in old_paths.items():
        if path not in new_paths:
            changes.append(Change(
                type=ChangeType.endpoint_removed,
                severity=ChangeSeverity.BREAKING,
                path=path,
                description=f"Endpoint {path} was removed"
            ))
            continue
            
        new_methods = new_paths[path]
        for method, old_op in old_methods.items():
            op_path = f"{path}.{method.upper()}"
            if method not in new_methods:
                changes.append(Change(
                    type=ChangeType.method_removed,
                    severity=ChangeSeverity.BREAKING,
                    path=op_path,
                    description=f"HTTP method {method.upper()} removed for {path}"
                ))
                continue
                
            new_op = new_methods[method]
            
            # Compare Parameters
            old_params = old_op.get('parameters', [])
            new_params = new_op.get('parameters', [])
            
            old_param_dict = {(p.get('name'), p.get('in')): get_schema(old_spec, p) for p in old_params if p.get('name') and p.get('in')}
            new_param_dict = {(p.get('name'), p.get('in')): get_schema(new_spec, p) for p in new_params if p.get('name') and p.get('in')}
            
            for (p_name, p_in), old_p in old_param_dict.items():
                p_path = f"{op_path}.parameters.{p_in}.{p_name}"
                if (p_name, p_in) not in new_param_dict:
                    changes.append(Change(
                        type=ChangeType.parameter_removed,
                        severity=ChangeSeverity.BREAKING,
                        path=p_path,
                        description=f"Parameter {p_name} in {p_in} was removed"
                    ))
                else:
                    new_p = new_param_dict[(p_name, p_in)]
                    old_p_schema = get_schema(old_spec, old_p.get('schema', {}))
                    new_p_schema = get_schema(new_spec, new_p.get('schema', {}))
                    old_p_type = old_p_schema.get('type')
                    new_p_type = new_p_schema.get('type')
                    if old_p_type and new_p_type and old_p_type != new_p_type:
                        changes.append(Change(
                            type=ChangeType.parameter_type_changed,
                            severity=ChangeSeverity.BREAKING,
                            path=p_path,
                            description=f"Parameter {p_name} type changed from {old_p_type} to {new_p_type}"
                        ))
                        
            for (p_name, p_in), new_p in new_param_dict.items():
                if (p_name, p_in) not in old_param_dict:
                    p_path = f"{op_path}.parameters.{p_in}.{p_name}"
                    is_required = new_p.get('required', False)
                    if is_required:
                        changes.append(Change(
                            type=ChangeType.required_parameter_added,
                            severity=ChangeSeverity.BREAKING,
                            path=p_path,
                            description=f"Required parameter {p_name} in {p_in} was added"
                        ))
                    else:
                        changes.append(Change(
                            type=ChangeType.parameter_added,
                            severity=ChangeSeverity.INFO,
                            path=p_path,
                            description=f"Optional parameter {p_name} in {p_in} was added"
                        ))
            
            # Compare Request Body
            old_req_body = old_op.get('requestBody', {})
            new_req_body = new_op.get('requestBody', {})
            
            if old_req_body or new_req_body:
                old_req_resolved = get_schema(old_spec, old_req_body)
                new_req_resolved = get_schema(new_spec, new_req_body)
                
                old_content = old_req_resolved.get('content', {})
                new_content = new_req_resolved.get('content', {})
                
                for media_type, old_media in old_content.items():
                    if media_type in new_content:
                        old_schema = old_media.get('schema', {})
                        new_schema = new_content[media_type].get('schema', {})
                        if old_schema and new_schema:
                            changes.extend(compare_schemas(
                                old_spec, new_spec, 
                                old_schema, new_schema, 
                                f"{op_path}.requestBody.content.{media_type}.schema"
                            ))
            
            # Compare Responses
            old_responses = old_op.get('responses', {})
            new_responses = new_op.get('responses', {})
            
            for status, old_res in old_responses.items():
                if status not in new_responses:
                    changes.append(Change(
                        type=ChangeType.response_removed,
                        severity=ChangeSeverity.BREAKING,
                        path=f"{op_path}.responses.{status}",
                        description=f"Response status {status} was removed",
                        metadata={"status_code": status}
                    ))
                else:
                    old_res_resolved = get_schema(old_spec, old_res)
                    new_res_resolved = get_schema(new_spec, new_responses[status])
                    
                    old_content = old_res_resolved.get('content', {})
                    new_content = new_res_resolved.get('content', {})
                    
                    for media_type, old_media in old_content.items():
                        if media_type in new_content:
                            old_schema = old_media.get('schema', {})
                            new_schema = new_content[media_type].get('schema', {})
                            if old_schema and new_schema:
                                changes.extend(compare_schemas(
                                    old_spec, new_spec, 
                                    old_schema, new_schema, 
                                    f"{op_path}.responses.{status}.content.{media_type}.schema"
                                ))
                                
    return DiffResult(changes=changes)
