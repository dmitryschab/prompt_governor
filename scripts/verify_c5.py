#!/usr/bin/env python3
"""
Verification script for Phase C5: API Router Integration

This script verifies that all API routes are properly configured
and accessible when the FastAPI application starts.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verify_imports():
    """Verify all imports work correctly."""
    print("Checking imports...")

    try:
        from mvp.main import app

        print("  ✓ main.py imports successfully")
    except Exception as e:
        print(f"  ✗ main.py import failed: {e}")
        return False

    try:
        from mvp.api import api_router

        print("  ✓ api/__init__.py imports successfully")
    except Exception as e:
        print(f"  ✗ api/__init__.py import failed: {e}")
        return False

    try:
        from mvp.api.prompts import router as prompts_router

        print("  ✓ api/prompts.py imports successfully")
    except Exception as e:
        print(f"  ✗ api/prompts.py import failed: {e}")
        return False

    try:
        from mvp.api.configs import router as configs_router

        print("  ✓ api/configs.py imports successfully")
    except Exception as e:
        print(f"  ✗ api/configs.py import failed: {e}")
        return False

    try:
        from mvp.api.documents import router as documents_router

        print("  ✓ api/documents.py imports successfully")
    except Exception as e:
        print(f"  ✗ api/documents.py import failed: {e}")
        return False

    try:
        from mvp.api.runs import router as runs_router

        print("  ✓ api/runs.py imports successfully")
    except Exception as e:
        print(f"  ✗ api/runs.py import failed: {e}")
        return False

    return True


def verify_routes():
    """Verify all routes are registered in the FastAPI app."""
    print("\nChecking routes...")

    from mvp.main import app

    routes = [route.path for route in app.routes]

    expected_routes = [
        # Health and test
        "/api/health",
        "/api/test/volumes",
        "/",
        # API routes (prefixed with /api)
        "/api/prompts",
        "/api/configs",
        "/api/documents",
        "/api/runs",
    ]

    all_found = True
    for route in expected_routes:
        # Check if route exists (may have path params)
        found = any(route in r or r.startswith(route + "/") for r in routes)
        if found:
            print(f"  ✓ {route}")
        else:
            print(f"  ✗ {route} NOT FOUND")
            all_found = False

    return all_found


def verify_error_handlers():
    """Verify error handlers are registered."""
    print("\nChecking error handlers...")

    from mvp.main import app
    from mvp.utils.errors import (
        NotFoundError,
        ValidationError,
        StorageError,
        PipelineError,
    )

    # Check if exception handlers are registered
    handlers = app.exception_handlers

    expected_exceptions = [
        NotFoundError,
        ValidationError,
        StorageError,
        PipelineError,
    ]

    all_found = True
    for exc in expected_exceptions:
        if exc in handlers:
            print(f"  ✓ Handler for {exc.__name__}")
        else:
            print(f"  ✗ Handler for {exc.__name__} NOT FOUND")
            all_found = False

    return all_found


def verify_middleware():
    """Verify middleware is configured."""
    print("\nChecking middleware...")

    from mvp.main import app

    # Check for CORS middleware
    has_cors = any(
        "CORSMiddleware" in str(type(middleware)) for middleware in app.user_middleware
    )

    if has_cors:
        print("  ✓ CORS middleware configured")
    else:
        print("  ✗ CORS middleware NOT FOUND")

    return has_cors


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Phase C5: API Router Integration - Verification")
    print("=" * 60)

    checks = [
        ("Imports", verify_imports),
        ("Routes", verify_routes),
        ("Error Handlers", verify_error_handlers),
        ("Middleware", verify_middleware),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check failed with exception: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All verification checks passed!")
        print("\nAPI endpoints available:")
        print("  - GET  /api/health          - Health check")
        print("  - GET  /api/test/volumes    - Test volume mounts")
        print("  - GET  /                    - Serve index.html")
        print("  - GET  /api/prompts         - List prompts")
        print("  - GET  /api/configs         - List configs")
        print("  - GET  /api/documents       - List documents")
        print("  - GET  /api/runs            - List runs")
        return 0
    else:
        print("\n⚠️  Some verification checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
