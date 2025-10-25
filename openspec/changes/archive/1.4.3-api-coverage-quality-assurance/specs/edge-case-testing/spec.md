# edge-case-testing Specification

## Purpose
系统化地测试边界条件、异常输入和安全攻击向量，确保系统在极端情况下稳定可靠。

## ADDED Requirements

### Requirement: Edge Case Test Data Generation
The system SHALL provide comprehensive edge case generators for systematic boundary testing.

#### Scenario: Generate invalid UUID test cases
- **GIVEN** need to test UUID validation
- **WHEN** invalid_uuids() generator is called
- **THEN** it SHALL return list of invalid UUID strings
- **AND** list SHALL include: non-UUID strings, numbers, nil UUID, malformed UUIDs
- **AND** list SHALL include security vectors: SQL injection, XSS, path traversal
- **AND** each case SHALL have descriptive label for test output

#### Scenario: Generate boundary integer test cases
- **GIVEN** need to test integer input validation
- **WHEN** boundary_integers() generator is called
- **THEN** it SHALL return list of boundary values
- **AND** list SHALL include: 0, negative numbers, INT_MAX, overflow values
- **AND** list SHALL test positive and negative edges
- **AND** each case SHALL have descriptive label

#### Scenario: Generate boundary string test cases
- **GIVEN** need to test string input validation
- **WHEN** boundary_strings() generator is called
- **THEN** it SHALL return list of edge case strings
- **AND** list SHALL include: empty string, whitespace, unicode, emoji
- **AND** list SHALL include: very long strings (1000, 10000 chars)
- **AND** list SHALL include: special characters, control characters
- **AND** list SHALL include: security vectors (XSS, SQL injection)

#### Scenario: Generate boundary date test cases
- **GIVEN** need to test date input validation
- **WHEN** boundary_dates() generator is called
- **THEN** it SHALL return list of edge case dates
- **AND** list SHALL include: today, past dates, future dates
- **AND** list SHALL include: epoch date, far future date
- **AND** list SHALL include: invalid dates (Feb 30, month 13)
- **AND** list SHALL include: invalid formats

### Requirement: Invalid Input Handling
All API endpoints SHALL handle invalid inputs gracefully without 500 errors.

#### Scenario: Invalid UUID in path parameters
- **GIVEN** API endpoint with UUID path parameter (e.g., /tasks/{task_id})
- **WHEN** request is made with invalid UUID in path
- **THEN** response SHALL be 422 Unprocessable Entity (FastAPI validation)
- **AND** response SHALL have UnifiedResponse format
- **AND** error message SHALL clearly indicate "invalid UUID format"
- **AND** system SHALL NOT return 500 Internal Server Error

#### Scenario: Invalid UUID in request body
- **GIVEN** API endpoint accepting UUID in JSON body
- **WHEN** request body contains invalid UUID string
- **THEN** response SHALL be 422 Unprocessable Entity
- **AND** error message SHALL indicate which field has invalid UUID
- **AND** system SHALL validate before business logic execution

#### Scenario: SQL injection attempts in UUID field
- **GIVEN** malicious input like "' OR '1'='1" in UUID field
- **WHEN** request is processed
- **THEN** input SHALL be rejected as invalid UUID format (422)
- **AND** NO SQL injection SHALL occur
- **AND** database queries SHALL use parameterized statements
- **AND** system logs SHALL record suspicious input

#### Scenario: XSS attempts in text fields
- **GIVEN** malicious input like "<script>alert('xss')</script>" in task content
- **WHEN** task is created and later retrieved
- **THEN** content SHALL be properly escaped/sanitized
- **AND** returned content SHALL NOT contain executable script tags
- **AND** frontend rendering SHALL be safe from XSS

#### Scenario: Path traversal attempts
- **GIVEN** malicious input like "../../../etc/passwd" in fields
- **WHEN** input is processed
- **THEN** input SHALL be treated as literal string (not file path)
- **AND** NO file system access SHALL occur
- **AND** system SHALL not leak file system information

### Requirement: Boundary Value Testing
All API endpoints SHALL handle boundary values correctly.

#### Scenario: Empty string in required text field
- **GIVEN** API endpoint requiring non-empty text (e.g., task content)
- **WHEN** request contains empty string or only whitespace
- **THEN** response SHALL be 422 Unprocessable Entity
- **AND** error message SHALL indicate "field cannot be empty"

#### Scenario: Extremely long string in text field
- **GIVEN** task content field with reasonable length limit
- **WHEN** request contains 10,000 character string
- **THEN** system SHALL either reject (422) or truncate with warning
- **AND** system SHALL NOT crash or hang
- **AND** database insertion SHALL not fail with size error

#### Scenario: Zero and negative integers in amount fields
- **GIVEN** API endpoint accepting integer amount (e.g., points)
- **WHEN** request contains 0 or negative value
- **THEN** validation SHALL match business logic (allow/reject based on context)
- **AND** negative amounts SHALL be allowed for deductions
- **AND** validation error SHALL be clear if rejected

#### Scenario: Integer overflow values
- **GIVEN** integer field in API
- **WHEN** request contains value > INT_MAX (2^31-1)
- **THEN** system SHALL handle gracefully (422 or conversion)
- **AND** system SHALL NOT cause integer overflow in database
- **AND** calculation results SHALL remain accurate

#### Scenario: Invalid date formats and non-existent dates
- **GIVEN** API endpoint accepting date string (e.g., Top3 date)
- **WHEN** request contains invalid format or non-existent date
- **THEN** response SHALL be 422 with clear error message
- **AND** date parsing SHALL validate calendar correctness
- **AND** leap year dates SHALL be handled correctly

### Requirement: Authorization and Permission Boundary Testing
All protected endpoints SHALL enforce authorization correctly at boundaries.

#### Scenario: Missing authentication token
- **GIVEN** protected API endpoint requiring authentication
- **WHEN** request is made without Authorization header
- **THEN** response SHALL be 401 Unauthorized
- **AND** error message SHALL indicate "authentication required"
- **AND** NO business logic SHALL execute

#### Scenario: Invalid or expired token
- **GIVEN** protected API endpoint
- **WHEN** request contains malformed or expired JWT token
- **THEN** response SHALL be 401 Unauthorized
- **AND** token validation SHALL occur before business logic
- **AND** error message SHALL distinguish "invalid token" vs "expired token"

#### Scenario: Cross-user resource access attempt
- **GIVEN** user A tries to access user B's resource (task, points, etc)
- **WHEN** user A provides valid token but wrong resource ID
- **THEN** response SHALL be 404 Not Found (hide existence) or 403 Forbidden
- **AND** resource data SHALL NOT be leaked
- **AND** operation SHALL NOT be performed

#### Scenario: Privilege escalation attempt
- **GIVEN** regular user tries to access admin-only endpoint
- **WHEN** request is made with regular user token
- **THEN** response SHALL be 403 Forbidden
- **AND** role check SHALL occur before business logic
- **AND** admin operations SHALL NOT execute

### Requirement: Data Constraint Violation Testing
System SHALL handle database constraint violations gracefully.

#### Scenario: Duplicate unique constraint violation
- **GIVEN** database table with unique constraint (e.g., phone number)
- **WHEN** INSERT or UPDATE violates unique constraint
- **THEN** system SHALL catch IntegrityError exception
- **AND** response SHALL be 422 with user-friendly message ("phone already exists")
- **AND** system SHALL NOT expose raw database error

#### Scenario: Foreign key constraint violation
- **GIVEN** database table with foreign key reference
- **WHEN** INSERT references non-existent foreign key
- **THEN** system SHALL validate foreign key existence before insertion
- **AND** response SHALL be 404 or 422 with clear message
- **AND** database constraint SHALL act as safety net

#### Scenario: NOT NULL constraint violation
- **GIVEN** database column with NOT NULL constraint
- **WHEN** INSERT or UPDATE tries to set column to NULL
- **THEN** validation layer SHALL catch null value before database
- **AND** response SHALL be 422 with field name and "required" message
- **AND** database constraint SHALL not be triggered

#### Scenario: CHECK constraint violation
- **GIVEN** database table with CHECK constraint (e.g., quantity >= 0)
- **WHEN** UPDATE tries to set invalid value
- **THEN** validation layer SHALL enforce constraint
- **AND** database CHECK SHALL act as additional safety
- **AND** error message SHALL explain business rule

### Requirement: Concurrency Edge Cases
System SHALL handle race conditions and timing edge cases.

#### Scenario: Double-click or repeated submission
- **GIVEN** user clicks submit button multiple times rapidly
- **WHEN** multiple identical requests arrive concurrently
- **THEN** idempotency mechanism SHALL prevent duplicate operations
- **AND** only first request SHALL succeed (or all succeed if idempotent)
- **AND** user SHALL see consistent result

#### Scenario: Resource deleted during operation
- **GIVEN** user A is operating on resource, user B deletes it concurrently
- **WHEN** user A's operation completes
- **THEN** operation SHALL fail gracefully with 404 Not Found
- **AND** system SHALL detect resource no longer exists
- **AND** NO partial state SHALL be left

#### Scenario: Balance check race condition
- **GIVEN** user has exactly 300 points
- **WHEN** two operations requiring 300 points happen concurrently
- **THEN** only one operation SHALL succeed
- **AND** the other SHALL fail with "insufficient balance"
- **AND** balance SHALL never go negative

### Requirement: Error Recovery and Partial Failure
System SHALL handle partial failures gracefully with proper rollback.

#### Scenario: Transaction rollback on error
- **GIVEN** complex operation with multiple database writes
- **WHEN** one write fails mid-transaction
- **THEN** entire transaction SHALL rollback
- **AND** database SHALL return to consistent state
- **AND** NO partial data SHALL be committed

#### Scenario: External service failure handling
- **GIVEN** operation depends on external service (e.g., AI chat)
- **WHEN** external service is unavailable or times out
- **THEN** system SHALL return 503 Service Unavailable or 500 with retry hint
- **AND** user data SHALL remain consistent
- **AND** operation SHALL be retryable

#### Scenario: Database connection loss during operation
- **GIVEN** operation in progress
- **WHEN** database connection is lost
- **THEN** system SHALL catch OperationalError exception
- **AND** system SHALL return 500 with "database unavailable" message
- **AND** system SHALL attempt connection recovery
- **AND** NO data corruption SHALL occur

### Requirement: Security Attack Vector Testing
System SHALL be resilient against common security attacks.

#### Scenario: Mass assignment vulnerability check
- **GIVEN** API endpoint accepting JSON body to update user profile
- **WHEN** request includes additional fields not intended (e.g., "is_admin": true)
- **THEN** system SHALL ignore unrecognized fields (Pydantic strict mode)
- **AND** only explicitly allowed fields SHALL be updated
- **AND** privilege fields SHALL NOT be modifiable via API

#### Scenario: Rate limiting boundary testing
- **GIVEN** API has rate limit (if implemented)
- **WHEN** excessive requests are sent in short time
- **THEN** system SHALL return 429 Too Many Requests after limit
- **AND** rate limit SHALL be per-user not global
- **AND** rate limit SHALL reset after time window

#### Scenario: Large payload attack (DoS)
- **GIVEN** API endpoint accepting JSON body
- **WHEN** request contains extremely large payload (10MB+)
- **THEN** system SHALL reject with 413 Payload Too Large
- **AND** system SHALL NOT attempt to parse entire payload
- **AND** system SHALL remain responsive for other requests

#### Scenario: Slowloris attack resilience
- **GIVEN** API has request timeout configuration
- **WHEN** client sends request very slowly (trickle)
- **THEN** server SHALL timeout request after configured limit
- **AND** server SHALL free resources (not hang indefinitely)
- **AND** server SHALL remain available for legitimate requests

## Cross-Reference
- **Depends on**:
  - 1.4.1-real-http-testing-framework-p0-fixes (requires real HTTP server)
  - 1.4.2-uuid-type-safety-p1-fixes (requires input validation)
- **Modifies**:
  - api-testing (adds edge case test suite)
- **Depended by**: None
