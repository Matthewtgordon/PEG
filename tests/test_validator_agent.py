"""
Tests for ValidatorAgent - Enhanced validation for generated code.

Tests include:
- Syntax validation
- Security scanning
- Sandboxed execution
- Test generation and running
- MCP compliance checking
"""

import pytest
from unittest.mock import Mock, patch

from apeg_core.agents.validator_agent import ValidatorAgent, ValidationReport


class TestValidationReport:
    """Tests for ValidationReport class."""

    def test_report_initialization(self):
        """Test report initialization."""
        report = ValidationReport()

        assert report.status == "pending"
        assert report.passed is False
        assert report.stages == {}
        assert report.errors == []

    def test_add_stage(self):
        """Test adding a stage to the report."""
        report = ValidationReport()

        report.add_stage("syntax", True, {"details": "ok"})

        assert "syntax" in report.stages
        assert report.stages["syntax"]["passed"] is True

    def test_add_failing_stage(self):
        """Test that failing stage adds error."""
        report = ValidationReport()

        report.add_stage("lint", False, {"errors": 5})

        assert report.stages["lint"]["passed"] is False
        assert len(report.errors) > 0

    def test_finalize_all_passed(self):
        """Test finalization with all stages passed."""
        report = ValidationReport()
        report.add_stage("stage1", True)
        report.add_stage("stage2", True)

        report.finalize()

        assert report.passed is True
        assert report.status == "passed"

    def test_finalize_with_failure(self):
        """Test finalization with failing stage."""
        report = ValidationReport()
        report.add_stage("stage1", True)
        report.add_stage("stage2", False)

        report.finalize()

        assert report.passed is False
        assert report.status == "failed"

    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = ValidationReport()
        report.add_stage("test", True)
        report.finalize()

        result = report.to_dict()

        assert "status" in result
        assert "passed" in result
        assert "stages" in result
        assert "errors" in result


class TestValidatorAgent:
    """Tests for ValidatorAgent."""

    @pytest.fixture
    def validator(self):
        """Create a ValidatorAgent in test mode."""
        return ValidatorAgent(test_mode=True)

    @pytest.fixture
    def real_validator(self):
        """Create a ValidatorAgent for real validation."""
        return ValidatorAgent(test_mode=False)

    def test_initialization(self, validator):
        """Test ValidatorAgent initialization."""
        assert validator.name == "ValidatorAgent"
        assert validator.test_mode is True

    def test_describe_capabilities(self, validator):
        """Test capability description."""
        caps = validator.describe_capabilities()

        assert "validate" in caps
        assert "lint_code" in caps
        assert "security_scan" in caps

    def test_execute_validate_action(self, validator):
        """Test execute with validate action."""
        result = validator.execute("validate", {
            "code": {"impl": "def test(): pass", "name": "test"},
            "spec": {}
        })

        assert result["status"] in ["success", "failed"]
        assert "report" in result

    def test_validate_test_mode(self, validator):
        """Test validation in test mode returns success."""
        code = {"impl": "def test(): pass", "name": "test"}
        report = validator.validate(code, {})

        assert report["status"] == "passed"
        assert report["passed"] is True

    def test_validate_valid_code(self, real_validator):
        """Test validation of valid code."""
        code = {
            "impl": '''
def agent_execute(action, context, config, test_mode):
    """Valid agent function."""
    return {"status": "success"}
''',
            "name": "valid_agent"
        }

        report = real_validator.validate(code, {})

        assert report["stages"]["syntax"]["passed"] is True

    def test_validate_syntax_error(self, real_validator):
        """Test validation catches syntax errors."""
        code = {
            "impl": "def broken(:\n    pass",
            "name": "broken"
        }

        report = real_validator.validate(code, {})

        assert report["stages"]["syntax"]["passed"] is False
        assert report["passed"] is False


class TestSyntaxValidation:
    """Tests for syntax validation."""

    @pytest.fixture
    def validator(self):
        return ValidatorAgent(test_mode=False)

    def test_valid_syntax(self, validator):
        """Test valid Python syntax."""
        result = validator._check_syntax("x = 1 + 2\nprint(x)")
        assert result["passed"] is True

    def test_invalid_syntax(self, validator):
        """Test invalid Python syntax."""
        result = validator._check_syntax("def broken(:\n    pass")

        assert result["passed"] is False
        assert "error" in result

    def test_empty_code(self, validator):
        """Test empty code is valid."""
        result = validator._check_syntax("")
        assert result["passed"] is True


class TestSecurityScan:
    """Tests for security scanning."""

    @pytest.fixture
    def validator(self):
        return ValidatorAgent(test_mode=False)

    def test_clean_code(self, validator):
        """Test code without security issues."""
        code = '''
def safe_function():
    return {"status": "success"}
'''
        result = validator.security_scan(code)

        assert result["high_severity"] == 0
        assert result["compliant"] is True

    def test_detects_eval(self, validator):
        """Test detection of eval()."""
        code = '''
def dangerous():
    return eval("1 + 1")
'''
        result = validator.security_scan(code)

        assert result["high_severity"] > 0
        assert result["compliant"] is False

    def test_detects_exec(self, validator):
        """Test detection of exec()."""
        code = '''
def dangerous():
    exec("pass")
'''
        result = validator.security_scan(code)

        assert result["high_severity"] > 0

    def test_detects_os_system(self, validator):
        """Test detection of os.system()."""
        code = '''
import os
def dangerous():
    os.system("ls")
'''
        result = validator.security_scan(code)

        assert result["high_severity"] > 0

    def test_detects_pickle(self, validator):
        """Test detection of pickle.loads()."""
        code = '''
import pickle
def dangerous(data):
    return pickle.loads(data)
'''
        result = validator.security_scan(code)

        assert result["high_severity"] > 0


class TestLinting:
    """Tests for code linting."""

    @pytest.fixture
    def validator(self):
        return ValidatorAgent(test_mode=False)

    def test_basic_lint(self, validator):
        """Test basic linting returns results."""
        code = '''
def clean_function():
    x = 1
    return x
'''
        result = validator.lint_code(code)

        assert "error_count" in result
        assert "warning_count" in result
        assert "score" in result

    def test_basic_lint_catches_bare_except(self, validator):
        """Test that basic lint catches bare except."""
        code = '''
def bad_function():
    try:
        pass
    except:
        pass
'''
        result = validator._basic_lint(code)

        assert result["warning_count"] > 0


class TestSandboxExecution:
    """Tests for sandboxed code execution."""

    @pytest.fixture
    def validator(self):
        return ValidatorAgent(test_mode=False, config={"timeout": 5})

    def test_successful_execution(self, validator):
        """Test successful code execution."""
        code = '''
def agent_execute(action, context, config, test_mode):
    return {"status": "success"}
'''
        result = validator.sandbox_exec(code)

        assert result["success"] is True
        assert "Execution successful" in result["output"]

    def test_execution_with_error(self, validator):
        """Test execution that raises an error."""
        code = '''
def agent_execute(action, context, config, test_mode):
    raise ValueError("Test error")
'''
        result = validator.sandbox_exec(code)

        # Should still complete but with error
        assert "output" in result or "error" in result


class TestTestGeneration:
    """Tests for test generation."""

    @pytest.fixture
    def validator(self):
        return ValidatorAgent(test_mode=False)

    def test_generate_tests(self, validator):
        """Test generating test cases."""
        spec = {
            "name": "test_agent",
            "capabilities": ["action1", "action2"]
        }

        tests = validator.generate_tests(spec)

        assert "test_basic_import" in tests
        assert "test_action1" in tests
        assert "test_action2" in tests


class TestMCPCompliance:
    """Tests for MCP compliance checking."""

    @pytest.fixture
    def validator(self):
        return ValidatorAgent(test_mode=False)

    def test_compliant_code(self, validator):
        """Test MCP compliant code."""
        code = '''
import logging
logger = logging.getLogger(__name__)

def agent_execute(action, context, config, test_mode):
    logger.info("Executing action")
    return {"status": "success"}
'''
        result = validator.check_mcp(code)

        assert result["compliant"] is True
        assert result["checks"]["audit_logging"] is True

    def test_non_compliant_code(self, validator):
        """Test non-MCP compliant code."""
        code = '''
def simple_function():
    pass
'''
        result = validator.check_mcp(code)

        # Should have recommendations
        assert len(result["recommendations"]) > 0

    def test_checks_error_handling(self, validator):
        """Test that error handling is checked."""
        code_with_error_handling = '''
def agent_execute(action, context, config, test_mode):
    try:
        return {"status": "success"}
    except Exception as e:
        return {"status": "error"}
'''
        result = validator.check_mcp(code_with_error_handling)

        assert result["checks"]["error_handling"] is True


class TestValidatorIntegration:
    """Integration tests for ValidatorAgent."""

    def test_full_validation_pipeline(self):
        """Test complete validation pipeline."""
        validator = ValidatorAgent(test_mode=False)

        code = {
            "impl": '''
import logging
logger = logging.getLogger(__name__)

def agent_execute(action, context, config, test_mode):
    """Execute an action."""
    logger.info("Executing %s", action)
    try:
        if test_mode:
            return {"status": "success", "result": "test"}
        return {"status": "success", "result": action}
    except Exception as e:
        logger.error("Error: %s", e)
        return {"status": "error", "error": str(e)}
''',
            "name": "integration_test_agent"
        }

        spec = {
            "name": "integration_test_agent",
            "capabilities": ["test_action"]
        }

        report = validator.validate(code, spec)

        # Should pass most checks
        assert report["stages"]["syntax"]["passed"] is True
        assert report["stages"]["security"]["passed"] is True
