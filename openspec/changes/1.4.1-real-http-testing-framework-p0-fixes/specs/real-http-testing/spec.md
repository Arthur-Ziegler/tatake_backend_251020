# real-http-testing Specification

## Purpose
建立基于真实HTTP服务器的测试基础设施，确保测试环境与生产环境100%一致，消除ASGI Transport导致的测试假阳性问题。

## ADDED Requirements

### Requirement: Real HTTP Server Test Infrastructure
The testing system SHALL provide a real HTTP server-based testing infrastructure that mirrors production environment exactly.

#### Scenario: pytest session-scoped HTTP server lifecycle
- **GIVEN** a pytest test session starts
- **WHEN** the live_api_server fixture is initialized
- **THEN** it SHALL start a real uvicorn server on port 8099 using subprocess
- **AND** it SHALL wait up to 10 seconds for the server to be ready
- **AND** it SHALL verify server health via /health endpoint
- **AND** it SHALL yield the server URL "http://localhost:8099"
- **AND** it SHALL terminate the server process when session ends
- **AND** it SHALL ensure the server process is fully stopped within 5 seconds

#### Scenario: Real HTTP client with proper configuration
- **GIVEN** a live API server is running
- **WHEN** the real_api_client fixture is created
- **THEN** it SHALL create an httpx.AsyncClient instance
- **AND** it SHALL configure base_url to the live server URL
- **AND** it SHALL set timeout to 10 seconds
- **AND** it SHALL enable follow_redirects
- **AND** it SHALL properly close the client after test completion

#### Scenario: Server startup failure handling
- **GIVEN** the live API server fixture attempts to start
- **WHEN** the server fails to start within 10 seconds
- **THEN** it SHALL terminate the subprocess
- **AND** it SHALL raise RuntimeError with clear error message
- **AND** it SHALL include subprocess stdout and stderr in error message

#### Scenario: Port conflict detection and handling
- **GIVEN** port 8099 is already in use
- **WHEN** the live API server fixture attempts to start
- **THEN** it SHALL detect the port conflict
- **AND** it SHALL raise RuntimeError indicating port is in use
- **AND** it SHALL provide guidance on how to resolve the conflict

###  Requirement: Test Data Management and Cleanup
The testing system SHALL provide automatic test data cleanup to prevent data pollution between tests.

#### Scenario: Automatic test data cleanup after each test
- **GIVEN** a test creates user data, tasks, points, or rewards
- **WHEN** the test completes (success or failure)
- **THEN** the auto_cleanup fixture SHALL identify all created test data
- **AND** it SHALL delete all tasks created by test users
- **AND** it SHALL adjust points balance to zero for test users
- **AND** it SHALL delete all reward records for test users
- **AND** it SHALL delete all Top3 records for test users
- **AND** it SHALL verify cleanup succeeded before next test starts

#### Scenario: Test user registration tracking
- **GIVEN** a test needs to create a new user
- **WHEN** it calls real_api_client.register_test_user()
- **THEN** the system SHALL call POST /auth/guest-init
- **AND** it SHALL track the created user_id in a cleanup list
- **AND** it SHALL return user credentials for test use
- **AND** it SHALL ensure the user is cleaned up after test

#### Scenario: Cleanup verification
- **GIVEN** the cleanup process completes
- **WHEN** verification queries are executed
- **THEN** test users SHALL have zero tasks
- **AND** test users SHALL have zero points balance
- **AND** test users SHALL have zero reward records
- **AND** test users SHALL have zero Top3 records

### Requirement: Migration from ASGI Transport to Real HTTP
The testing system SHALL completely migrate from ASGI Transport-based tests to real HTTP-based tests.

#### Scenario: Remove all ASGI Transport test code
- **GIVEN** the codebase contains tests using ASGITransport
- **WHEN** the migration is complete
- **THEN** searching for "ASGITransport" in tests/ SHALL return zero results
- **AND** searching for "TestClient" in tests/ SHALL return zero results
- **AND** all test files SHALL use real_api_client fixture
- **AND** no test SHALL import from httpx.ASGITransport

#### Scenario: Update conftest.py to remove old fixtures
- **GIVEN** tests/conftest.py contains old test_client fixture
- **WHEN** the migration is complete
- **THEN** the old test_client fixture SHALL be removed
- **AND** only real HTTP-based fixtures SHALL remain
- **AND** the file SHALL import from tests.conftest_real_http

#### Scenario: Deprecated test file handling
- **GIVEN** test files that cannot be easily migrated in this phase
- **WHEN** those files are identified
- **THEN** they SHALL be marked with # TODO: Migrate to real HTTP in phase 3
- **AND** they SHALL be skipped in pytest execution
- **AND** a list of deprecated files SHALL be documented in tests/MIGRATION.md

### Requirement: Test Performance Optimization
The real HTTP testing system SHALL maintain acceptable test execution performance.

#### Scenario: Server startup time optimization
- **GIVEN** the live API server needs to start
- **WHEN** subprocess.Popen is called
- **THEN** it SHALL use --reload=false flag to disable hot reload
- **AND** it SHALL use --log-level=error to reduce logging overhead
- **AND** it SHALL complete startup within 3 seconds
- **AND** it SHALL be reused across all tests in the session

#### Scenario: Individual test execution time
- **GIVEN** a single API test using real HTTP client
- **WHEN** the test makes HTTP requests to the live server
- **THEN** the test SHALL complete within 200ms for simple operations
- **AND** complex operations SHALL complete within 2 seconds
- **AND** tests SHALL not wait unnecessarily between assertions

#### Scenario: Total test suite execution time for Phase 1
- **GIVEN** Phase 1 includes approximately 10 critical API tests
- **WHEN** the entire Phase 1 test suite runs
- **THEN** total execution time SHALL be under 1 minute
- **AND** it SHALL include server startup, all tests, and cleanup
- **AND** performance metrics SHALL be logged for monitoring

### Requirement: Test Documentation and Developer Experience
The testing system SHALL provide clear documentation and excellent developer experience.

#### Scenario: README documentation for real HTTP testing
- **GIVEN** a developer reads tests/README.md
- **WHEN** they want to run real HTTP tests
- **THEN** the README SHALL explain how to start the test suite
- **AND** it SHALL document the live_api_server fixture usage
- **AND** it SHALL explain the cleanup mechanism
- **AND** it SHALL provide troubleshooting guidance for common issues
- **AND** it SHALL include example test code snippets

#### Scenario: Clear error messages for test failures
- **GIVEN** a real HTTP test fails
- **WHEN** pytest displays the failure
- **THEN** the error message SHALL clearly indicate:
  - Which API endpoint failed
  - Expected vs actual HTTP status code
  - Expected vs actual response body
  - Any relevant server logs
- **AND** it SHALL provide actionable debugging information

#### Scenario: Test isolation verification
- **GIVEN** multiple tests run in sequence
- **WHEN** test A creates data and test B runs after
- **THEN** test B SHALL NOT see test A's data
- **AND** each test SHALL start with a clean state
- **AND** test failures SHALL NOT affect subsequent tests

## MODIFIED Requirements

### Requirement: API Testing Coverage (from api-testing spec)
**Modification**: All API tests SHALL now use real HTTP requests instead of ASGI Transport.

#### Scenario: Task completion API testing with real HTTP
- **GIVEN** the task completion endpoint is being tested
- **WHEN** tests make POST requests to /tasks/{id}/complete
- **THEN** requests SHALL go through a real HTTP server
- **AND** all middleware SHALL be executed
- **AND** routing prefix SHALL be properly handled
- **AND** authentication SHALL work exactly as in production

## Cross-Reference
- **Depends on**: None (foundational capability)
- **Depended by**:
  - critical-bug-fixes (requires real HTTP testing for verification)
  - 1.4.2-uuid-type-safety-p1-fixes (Phase 2 will build on this foundation)
  - 1.4.3-api-coverage-quality-assurance (Phase 3 will extend this framework)
