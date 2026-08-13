import pytest
from app.services.contract_parser import ContractParser, SecurityError

def test_parse_json():
    content = '{"openapi": "3.0.0", "info": {"title": "Test"}}'
    result = ContractParser.parse_content(content)
    assert result["openapi"] == "3.0.0"

def test_parse_yaml():
    content = '''
openapi: 3.0.0
info:
  title: Test
'''
    result = ContractParser.parse_content(content)
    assert result["openapi"] == "3.0.0"

def test_parse_invalid():
    with pytest.raises(ValueError):
        ContractParser.parse_content('not valid json or yaml: : :')

def test_is_safe_url_rejects_localhost():
    with pytest.raises(SecurityError, match="restricted IP"):
        ContractParser._is_safe_url("http://localhost/spec.json")

def test_is_safe_url_rejects_file_scheme():
    with pytest.raises(SecurityError, match="Unsupported scheme"):
        ContractParser._is_safe_url("file:///etc/passwd")

def test_is_safe_url_allows_public(monkeypatch):
    # Mock DNS resolution to return a public IP
    monkeypatch.setattr("socket.gethostbyname", lambda x: "8.8.8.8")
    assert ContractParser._is_safe_url("https://api.github.com/openapi.yaml") == True
