# api-endpoint-coverage Specification

## Purpose
实现100%API端点覆盖率测试，确保所有API端点都经过充分测试，不遗漏任何功能。

## ADDED Requirements

### Requirement: Endpoint Discovery and Coverage Tracking
The system SHALL provide automated endpoint discovery and coverage tracking to ensure 100% API coverage.

#### Scenario: Discover all API endpoints from FastAPI routes
- **GIVEN** a FastAPI application with multiple domains
- **WHEN** endpoint discovery tool scans the application
- **THEN** it SHALL find all APIRoute definitions
- **AND** it SHALL extract path, method, name, module for each endpoint
- **AND** it SHALL exclude OPTIONS and HEAD methods (auto-generated)
- **AND** it SHALL return complete endpoint list with signatures

#### Scenario: Scan test code to find tested endpoints
- **GIVEN** test files containing HTTP client calls
- **WHEN** test scanner parses Python AST
- **THEN** it SHALL find all client.get/post/put/delete/patch calls
- **AND** it SHALL extract URL paths from string literals and f-strings
- **AND** it SHALL handle path parameters (convert {task_id} to pattern)
- **AND** it SHALL return set of tested endpoint signatures

#### Scenario: Calculate coverage rate by domain
- **GIVEN** all endpoints and tested endpoints are identified
- **WHEN** coverage report is generated
- **THEN** it SHALL calculate overall coverage rate
- **AND** it SHALL group endpoints by domain (extracted from path prefix)
- **AND** it SHALL calculate per-domain coverage rates
- **AND** it SHALL list untested endpoints with details

#### Scenario: Assert 100% coverage in test
- **GIVEN** endpoint coverage report is generated
- **WHEN** test_api_coverage.py runs
- **THEN** it SHALL assert coverage_rate == 1.0
- **AND** it SHALL fail with clear message listing untested endpoints
- **AND** it SHALL print detailed report showing total, tested, by-domain stats

### Requirement: Complete Task Domain Endpoint Coverage
The Task domain SHALL have 100% endpoint coverage with comprehensive test scenarios.

#### Scenario: Test GET /tasks - list all tasks
- **GIVEN** a user with multiple tasks (active, completed, deleted)
- **WHEN** GET /tasks is called
- **THEN** it SHALL return only active and completed tasks
- **AND** it SHALL NOT return deleted tasks
- **AND** it SHALL return tasks sorted by created_at DESC
- **AND** response SHALL have UnifiedResponse format

#### Scenario: Test POST /tasks/create - create task
- **GIVEN** authenticated user with valid token
- **WHEN** POST /tasks/create is called with task content
- **THEN** it SHALL create task in database
- **AND** it SHALL return task data with generated UUID
- **AND** it SHALL set is_completed=false, is_deleted=false by default
- **AND** it SHALL set created_at to current time

#### Scenario: Test PATCH /tasks/{task_id}/complete - complete task
- **GIVEN** an active task belonging to user
- **WHEN** PATCH /tasks/{task_id}/complete is called
- **THEN** it SHALL set is_completed=true
- **AND** it SHALL set completed_at to current time
- **AND** request body SHALL be optional (Bug #1 fix verification)
- **AND** response SHALL include updated task data

#### Scenario: Test DELETE /tasks/{task_id} - soft delete task
- **GIVEN** a task belonging to user
- **WHEN** DELETE /tasks/{task_id} is called
- **THEN** it SHALL set is_deleted=true (soft delete)
- **AND** it SHALL NOT physically delete from database
- **AND** subsequent GET /tasks SHALL NOT return this task
- **AND** response SHALL confirm deletion

#### Scenario: Test permission control for task operations
- **GIVEN** two users A and B, task belongs to user A
- **WHEN** user B tries to complete/delete task A
- **THEN** request SHALL be rejected with 404 or 403
- **AND** error message SHALL indicate permission denied
- **AND** task data SHALL NOT be modified

### Requirement: Complete Points Domain Endpoint Coverage
The Points domain SHALL have 100% endpoint coverage with correct API paths.

#### Scenario: Test GET /points/my-points - get current balance
- **GIVEN** a user with transaction history
- **WHEN** GET /points/my-points is called
- **THEN** response SHALL include current_balance field
- **AND** response SHALL include total_earned and total_spent statistics
- **AND** calculation SHALL match sum of all transactions
- **AND** UUID handling SHALL work without errors (Bug #3 fix verification)

#### Scenario: Test GET /points/transactions - get transaction history
- **GIVEN** a user with multiple transactions
- **WHEN** GET /points/transactions is called with pagination params
- **THEN** response SHALL return array of transactions
- **AND** each transaction SHALL have id, amount, source_type, created_at
- **AND** transactions SHALL be sorted by created_at DESC
- **AND** pagination SHALL work correctly (limit, offset)

#### Scenario: Verify incorrect paths are removed
- **GIVEN** the API may have had incorrect path /points/balance
- **WHEN** code review is performed
- **THEN** GET /points/balance endpoint SHALL NOT exist
- **AND** only /points/my-points SHALL be the correct balance endpoint
- **AND** OpenAPI docs SHALL reflect correct paths only

### Requirement: Complete Reward Domain Endpoint Coverage
The Reward domain SHALL have 100% endpoint coverage with data persistence verification.

#### Scenario: Test POST /user/welcome-gift/claim - claim welcome gift
- **GIVEN** a new user who has not claimed welcome gift
- **WHEN** POST /user/welcome-gift/claim is called
- **THEN** system SHALL write 1000 points to points_transactions table
- **AND** system SHALL write 3 reward items to user_rewards table
- **AND** system SHALL flush and verify write within transaction
- **AND** response SHALL include points_awarded and rewards_granted
- **AND** second attempt SHALL fail with "already claimed" error

#### Scenario: Test GET /rewards/my-rewards - get user rewards
- **GIVEN** a user with claimed welcome gift rewards
- **WHEN** GET /rewards/my-rewards is called
- **THEN** response SHALL return rewards dict grouped by reward_id
- **AND** each reward SHALL have correct quantity
- **AND** total_types SHALL equal number of distinct reward types
- **AND** UUID handling SHALL work without errors (Bug #5 fix verification)

#### Scenario: Test empty rewards case
- **GIVEN** a new user with no rewards
- **WHEN** GET /rewards/my-rewards is called
- **THEN** response SHALL return {rewards: {}, total_types: 0}
- **AND** response SHALL NOT be null or error
- **AND** response format SHALL be consistent with non-empty case

### Requirement: Complete Top3 Domain Endpoint Coverage
The Top3 domain SHALL have 100% endpoint coverage with UUID safety.

#### Scenario: Test POST /top3/set - set Top3 tasks
- **GIVEN** a user with 3 tasks and 300+ points balance
- **WHEN** POST /top3/set is called with date and task_ids
- **THEN** system SHALL deduct 300 points
- **AND** system SHALL create Top3 record with task_ids
- **AND** UUID conversions SHALL work correctly (Bug #6 fix verification)
- **AND** response SHALL include remaining_balance

#### Scenario: Test GET /top3 - get Top3 for date
- **GIVEN** a user has set Top3 for specific date
- **WHEN** GET /top3 is called with date parameter
- **THEN** response SHALL return task_ids for that date
- **AND** response SHALL include points_consumed and created_at
- **AND** if no Top3 set, response SHALL return empty task_ids (not 404)

#### Scenario: Test duplicate date prevention
- **GIVEN** user has already set Top3 for date X
- **WHEN** POST /top3/set is called again for date X
- **THEN** request SHALL be rejected with 422 error
- **AND** error message SHALL indicate "already set for this date"
- **AND** points SHALL NOT be deducted

### Requirement: Complete User Domain Endpoint Coverage
The User domain SHALL have 100% endpoint coverage with unified session dependency.

#### Scenario: Test POST /user/register - user registration
- **GIVEN** valid phone number and verification code
- **WHEN** POST /user/register is called
- **THEN** system SHALL create user account
- **AND** system SHALL return user_id and auth_token
- **AND** phone number SHALL be unique

#### Scenario: Test POST /user/login - user login
- **GIVEN** registered user with phone and verification code
- **WHEN** POST /user/login is called
- **THEN** system SHALL validate credentials
- **AND** system SHALL return auth_token
- **AND** token SHALL be valid for subsequent requests

#### Scenario: Test GET /user/profile - get user profile
- **GIVEN** authenticated user
- **WHEN** GET /user/profile is called with token
- **THEN** endpoint SHALL use SessionDep not get_user_session (Bug #7 fix)
- **AND** response SHALL return user data (id, phone, nickname, etc)
- **AND** response SHALL NOT include sensitive data (password_hash)

#### Scenario: Test PUT /user/profile - update user profile
- **GIVEN** authenticated user
- **WHEN** PUT /user/profile is called with update data
- **THEN** system SHALL update allowed fields (nickname, avatar_url)
- **AND** system SHALL NOT allow updating phone or user_id
- **AND** response SHALL return updated user data

#### Scenario: Test deleted endpoints return 404
- **GIVEN** avatar and feedback features are removed (Bug #8)
- **WHEN** POST /user/avatar is called
- **THEN** response SHALL be 404 Not Found
- **AND** OpenAPI documentation SHALL NOT include this endpoint
- **WHEN** POST /user/feedback is called
- **THEN** response SHALL be 404 Not Found

### Requirement: Complete Chat Domain Endpoint Coverage
The Chat domain SHALL have 100% endpoint coverage.

#### Scenario: Test POST /chat/session/start - start chat session
- **GIVEN** authenticated user
- **WHEN** POST /chat/session/start is called
- **THEN** system SHALL create new chat session
- **AND** response SHALL return session_id
- **AND** session SHALL be associated with user

#### Scenario: Test POST /chat/message - send message
- **GIVEN** active chat session
- **WHEN** POST /chat/message is called with message content
- **THEN** system SHALL save user message
- **AND** system SHALL generate AI response
- **AND** response SHALL return message_id and AI response

#### Scenario: Test GET /chat/history - get chat history
- **GIVEN** chat session with multiple messages
- **WHEN** GET /chat/history is called with session_id
- **THEN** response SHALL return all messages in chronological order
- **AND** each message SHALL have role (user/assistant), content, timestamp

## Cross-Reference
- **Depends on**:
  - 1.4.1-real-http-testing-framework-p0-fixes (requires real HTTP infrastructure)
  - 1.4.2-uuid-type-safety-p1-fixes (requires type-safe code base)
- **Modifies**:
  - api-testing (adds 100% endpoint coverage tests)
- **Depended by**: None (final phase)
