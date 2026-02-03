"""
Response Models Unit Tests

Tests for standard API response models.
"""

import pytest
from typing import List


class TestAPIResponse:
    """Tests for APIResponse model."""

    def test_default_success_true(self):
        """APIResponse should default success to True."""
        from src.utils.response_models import APIResponse

        response = APIResponse()

        assert response.success is True

    def test_default_fields_are_none(self):
        """APIResponse should default optional fields to None."""
        from src.utils.response_models import APIResponse

        response = APIResponse()

        assert response.data is None
        assert response.message is None
        assert response.error is None

    def test_with_data(self):
        """APIResponse should accept data."""
        from src.utils.response_models import APIResponse

        data = {"id": 1, "name": "Test"}
        response = APIResponse(data=data)

        assert response.data == data

    def test_with_all_fields(self):
        """APIResponse should accept all fields."""
        from src.utils.response_models import APIResponse

        response = APIResponse(
            success=False,
            data=None,
            message="Operation failed",
            error="Something went wrong"
        )

        assert response.success is False
        assert response.message == "Operation failed"
        assert response.error == "Something went wrong"

    def test_json_serialization(self):
        """APIResponse should serialize to JSON."""
        from src.utils.response_models import APIResponse

        response = APIResponse(
            success=True,
            data={"items": [1, 2, 3]},
            message="Success"
        )

        json_data = response.model_dump()

        assert json_data["success"] is True
        assert json_data["data"]["items"] == [1, 2, 3]


class TestPaginatedResponse:
    """Tests for PaginatedResponse model."""

    def test_default_values(self):
        """PaginatedResponse should have sensible defaults."""
        from src.utils.response_models import PaginatedResponse

        response = PaginatedResponse()

        assert response.success is True
        assert response.data == []
        assert response.count == 0
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 20

    def test_with_pagination_data(self):
        """PaginatedResponse should accept pagination data."""
        from src.utils.response_models import PaginatedResponse

        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = PaginatedResponse(
            data=items,
            count=3,
            total=100,
            page=5,
            page_size=3
        )

        assert response.data == items
        assert response.count == 3
        assert response.total == 100
        assert response.page == 5
        assert response.page_size == 3

    def test_data_is_list(self):
        """PaginatedResponse data should be a list."""
        from src.utils.response_models import PaginatedResponse

        response = PaginatedResponse()

        assert isinstance(response.data, list)


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_success_always_false(self):
        """ErrorResponse should have success=False."""
        from src.utils.response_models import ErrorResponse

        response = ErrorResponse(error="Test error")

        assert response.success is False

    def test_requires_error(self):
        """ErrorResponse should require error message."""
        from src.utils.response_models import ErrorResponse
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ErrorResponse()

    def test_optional_detail_and_code(self):
        """ErrorResponse should have optional detail and code."""
        from src.utils.response_models import ErrorResponse

        response = ErrorResponse(error="Error")

        assert response.detail is None
        assert response.code is None

    def test_with_all_fields(self):
        """ErrorResponse should accept all fields."""
        from src.utils.response_models import ErrorResponse

        response = ErrorResponse(
            error="Validation failed",
            detail="Field 'email' is required",
            code="VALIDATION_ERROR"
        )

        assert response.error == "Validation failed"
        assert response.detail == "Field 'email' is required"
        assert response.code == "VALIDATION_ERROR"


class TestSuccessResponseHelper:
    """Tests for success_response helper function."""

    def test_minimal_response(self):
        """success_response with no args should return minimal dict."""
        from src.utils.response_models import success_response

        result = success_response()

        assert result == {"success": True}

    def test_with_data(self):
        """success_response with data should include it."""
        from src.utils.response_models import success_response

        data = {"id": 1, "name": "Test"}
        result = success_response(data=data)

        assert result["success"] is True
        assert result["data"] == data

    def test_with_message(self):
        """success_response with message should include it."""
        from src.utils.response_models import success_response

        result = success_response(message="Operation completed")

        assert result["success"] is True
        assert result["message"] == "Operation completed"

    def test_with_data_and_message(self):
        """success_response with both data and message."""
        from src.utils.response_models import success_response

        result = success_response(data={"id": 1}, message="Created")

        assert result["success"] is True
        assert result["data"]["id"] == 1
        assert result["message"] == "Created"

    def test_data_none_not_included(self):
        """success_response should not include data key if None."""
        from src.utils.response_models import success_response

        result = success_response(data=None)

        assert "data" not in result

    def test_message_empty_not_included(self):
        """success_response should not include message if empty string."""
        from src.utils.response_models import success_response

        result = success_response(message="")

        assert "message" not in result


class TestErrorResponseHelper:
    """Tests for error_response helper function."""

    def test_minimal_error(self):
        """error_response with just error message."""
        from src.utils.response_models import error_response

        result = error_response("Something went wrong")

        assert result["success"] is False
        assert result["error"] == "Something went wrong"

    def test_with_detail(self):
        """error_response with detail should include it."""
        from src.utils.response_models import error_response

        result = error_response("Error", detail="More details here")

        assert result["success"] is False
        assert result["error"] == "Error"
        assert result["detail"] == "More details here"

    def test_with_code(self):
        """error_response with code should include it."""
        from src.utils.response_models import error_response

        result = error_response("Error", code="ERR_001")

        assert result["success"] is False
        assert result["error"] == "Error"
        assert result["code"] == "ERR_001"

    def test_with_all_params(self):
        """error_response with all params."""
        from src.utils.response_models import error_response

        result = error_response(
            "Validation failed",
            detail="Email is invalid",
            code="VALIDATION_ERROR"
        )

        assert result["success"] is False
        assert result["error"] == "Validation failed"
        assert result["detail"] == "Email is invalid"
        assert result["code"] == "VALIDATION_ERROR"

    def test_detail_none_not_included(self):
        """error_response should not include detail if None."""
        from src.utils.response_models import error_response

        result = error_response("Error", detail=None)

        assert "detail" not in result

    def test_code_none_not_included(self):
        """error_response should not include code if None."""
        from src.utils.response_models import error_response

        result = error_response("Error", code=None)

        assert "code" not in result
