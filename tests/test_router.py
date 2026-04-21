from app.schemas.chat import TaskType
from app.services.router_service import RouterService


def test_router_detects_image_request() -> None:
    router = RouterService()
    result = router.route("Generálj képet egy futurisztikus városról.")
    assert result.task_type == TaskType.image


def test_router_detects_image_request_with_natural_hungarian_phrase() -> None:
    router = RouterService()
    result = router.route("készíts egy képet, orbán viktorról és magyar péterről")
    assert result.task_type == TaskType.image


def test_router_detects_image_request_with_kernek_phrase() -> None:
    router = RouterService()
    result = router.route("kérnék egy képet egy sexy csajról")
    assert result.task_type == TaskType.image


def test_router_detects_code_request() -> None:
    router = RouterService()
    result = router.route("Írj egy Python scriptet ami átnevezi a fájlokat.")
    assert result.task_type == TaskType.code


def test_router_defaults_to_chat() -> None:
    router = RouterService()
    result = router.route("Mesélj röviden Budapest történelméről.")
    assert result.task_type == TaskType.chat
