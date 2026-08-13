import pytest
from app.services.openapi_diff import compare_openapi_specs
from app.models.diff_result import ChangeType, ChangeSeverity

def test_probable_rename():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "user_id": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.probable_rename
    assert diff.changes[0].severity == ChangeSeverity.WARNING
    assert diff.changes[0].metadata["old_name"] == "user_id"
    assert diff.changes[0].metadata["new_name"] == "id"

def test_property_removal():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.field_removed
    assert diff.changes[0].severity == ChangeSeverity.BREAKING

def test_required_property_addition():
    old_spec = {
        "paths": {
            "/users": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"}
                                    },
                                    "required": ["name"]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    new_spec = {
        "paths": {
            "/users": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"}
                                    },
                                    "required": ["name", "email"]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.required_field_added
    assert diff.changes[0].severity == ChangeSeverity.BREAKING
    
def test_endpoint_removal():
    old_spec = {
        "paths": {
            "/users": {"get": {}},
            "/posts": {"get": {}}
        }
    }
    
    new_spec = {
        "paths": {
            "/users": {"get": {}}
        }
    }
    
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.endpoint_removed
    assert diff.changes[0].severity == ChangeSeverity.BREAKING
    assert diff.changes[0].path == "/posts"
    
def test_non_breaking_optional_property_addition():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "age": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.field_added
    assert diff.changes[0].severity == ChangeSeverity.INFO
    assert diff.changes[0].metadata["prop_name"] == "age"
    
def test_incompatible_type_change():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "age": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "age": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.type_changed
    assert diff.changes[0].severity == ChangeSeverity.BREAKING
    assert diff.changes[0].metadata["old_type"] == "string"
    assert diff.changes[0].metadata["new_type"] == "integer"
    
def test_ambiguous_rename_not_reported():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "user_id": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id1": {"type": "string"},
                                            "id2": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    diff = compare_openapi_specs(old_spec, new_spec)
    # Should report 1 removal and 2 additions, not a rename
    assert len(diff.changes) == 3
    types = set(c.type for c in diff.changes)
    assert ChangeType.probable_rename not in types
    assert ChangeType.field_removed in types
    assert ChangeType.field_added in types

def test_refs_resolution():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"}
                    }
                }
            }
        }
    }
    
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"}
                    }
                }
            }
        }
    }
    
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.field_added
    assert diff.changes[0].severity == ChangeSeverity.INFO
    assert diff.changes[0].metadata["prop_name"] == "name"

def test_response_removed():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {"description": "OK"},
                        "404": {"description": "Not Found"}
                    }
                }
            }
        }
    }
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {"description": "OK"}
                    }
                }
            }
        }
    }
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.response_removed
    assert diff.changes[0].severity == ChangeSeverity.BREAKING
    assert diff.changes[0].metadata["status_code"] == "404"

def test_required_query_parameter_added():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "parameters": []
                }
            }
        }
    }
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {"name": "id", "in": "query", "required": True, "schema": {"type": "string"}}
                    ]
                }
            }
        }
    }
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.required_parameter_added
    assert diff.changes[0].severity == ChangeSeverity.BREAKING

def test_optional_query_parameter_added():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "parameters": []
                }
            }
        }
    }
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}}
                    ]
                }
            }
        }
    }
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.parameter_added
    assert diff.changes[0].severity == ChangeSeverity.INFO

def test_parameter_removed():
    old_spec = {
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {"name": "id", "in": "query", "schema": {"type": "string"}}
                    ]
                }
            }
        }
    }
    new_spec = {
        "paths": {
            "/users": {
                "get": {
                    "parameters": []
                }
            }
        }
    }
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.parameter_removed
    assert diff.changes[0].severity == ChangeSeverity.BREAKING

def test_endpoint_added():
    old_spec = {
        "paths": {
            "/users": {"get": {}}
        }
    }
    new_spec = {
        "paths": {
            "/users": {"get": {}},
            "/posts": {"get": {}}
        }
    }
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.endpoint_added
    assert diff.changes[0].severity == ChangeSeverity.INFO
    assert diff.changes[0].path == "/posts"

def test_method_added():
    old_spec = {
        "paths": {
            "/users": {"get": {}}
        }
    }
    new_spec = {
        "paths": {
            "/users": {"get": {}, "post": {}}
        }
    }
    diff = compare_openapi_specs(old_spec, new_spec)
    assert len(diff.changes) == 1
    assert diff.changes[0].type == ChangeType.method_added
    assert diff.changes[0].severity == ChangeSeverity.INFO
    assert diff.changes[0].path == "/users.POST"
