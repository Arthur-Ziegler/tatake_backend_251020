# critical-bug-fixes Specification

## Purpose
修复两个P0级阻塞性bug，使任务完成和Top3功能立即可用。这些是阻止用户正常使用系统的关键缺陷。

## MODIFIED Requirements

### Requirement: Task Completion API Request Body Handling
The task completion API SHALL accept empty request bodies to support the most common use case of completing a task without additional feedback.

#### Scenario: Complete task without request body (most common case)
- **GIVEN** a user wants to complete a task without providing mood feedback
- **WHEN** POST /tasks/{task_id}/complete is called with empty body
- **THEN** the API SHALL accept the request without error
- **AND** it SHALL NOT return 422 validation error
- **AND** it SHALL successfully mark the task as completed
- **AND** it SHALL return UnifiedResponse with code 200
- **AND** mood_feedback SHALL be None in the completion record

**Code Location**: `src/domains/task/router.py:444-480`

**Change Details**:
```python
# BEFORE (INCORRECT)
async def complete_task(
    task_id: UUID,
    request: CompleteTaskRequest = Body(...),  # ❌ Required body
)

# AFTER (CORRECT)
async def complete_task(
    task_id: UUID,
    request: Optional[CompleteTaskRequest] = Body(None),  # ✅ Optional body
)
```

#### Scenario: Complete task with mood feedback (optional enhancement)
- **GIVEN** a user wants to provide detailed feedback when completing a task
- **WHEN** POST /tasks/{task_id}/complete is called with mood_feedback in body
- **THEN** the API SHALL accept the request
- **AND** it SHALL store the mood_feedback data
- **AND** it SHALL return the feedback in the response
- **AND** the feedback SHALL include comment and difficulty fields

#### Scenario: Backward compatibility with existing clients
- **GIVEN** existing clients may send requests with or without body
- **WHEN** either format is used
- **THEN** the API SHALL handle both cases correctly
- **AND** it SHALL NOT break existing integrations
- **AND** OpenAPI documentation SHALL reflect both use cases

#### Scenario: Validation of request body when provided
- **GIVEN** a request body is provided
- **WHEN** the body contains invalid mood_feedback data
- **THEN** the API SHALL return 422 validation error
- **AND** error message SHALL clearly indicate which fields are invalid
- **AND** it SHALL provide guidance on correct format

### Requirement: Top3 System UUID Type Handling
The Top3 system SHALL properly handle UUID type conversions when interacting with the Points service.

#### Scenario: Set Top3 with UUID-to-string conversion
- **GIVEN** a user wants to set their Top3 tasks
- **WHEN** POST /tasks/special/top3 is called
- **THEN** the Top3Service SHALL receive user_id as UUID
- **AND** it SHALL convert UUID to string before calling points_service.get_balance()
- **AND** it SHALL NOT raise AttributeError about 'replace' method
- **AND** it SHALL successfully deduct 300 points
- **AND** it SHALL return Top3Response with remaining balance

**Code Location**: `src/domains/top3/service.py:48`

**Change Details**:
```python
# BEFORE (INCORRECT)
current_balance = self.points_service.get_balance(user_id)  # UUID object

# AFTER (CORRECT)
current_balance = self.points_service.get_balance(str(user_id))  # ✅ String
```

#### Scenario: All Top3 Service methods handle UUID properly
- **GIVEN** Top3 Service methods receive UUID parameters
- **WHEN** any method needs to interact with Points Service
- **THEN** it SHALL convert UUID to string explicitly
- **AND** it SHALL apply this pattern consistently:
  - set_top3() method
  - get_top3() method
  - is_task_in_today_top3() method
- **AND** no method SHALL pass raw UUID to services expecting strings

#### Scenario: Type safety documentation in code comments
- **GIVEN** the UUID handling code is written
- **WHEN** developers read the code
- **THEN** comments SHALL explain the type conversion requirement
- **AND** comments SHALL reference the comprehensive type safety fix in Phase 2
- **AND** TODO comments SHALL mark areas for Phase 2 improvement

#### Scenario: Integration test verification
- **GIVEN** the Top3 UUID fix is applied
- **WHEN** integration tests run with real HTTP requests
- **THEN** setting Top3 SHALL NOT raise UUID-related errors
- **AND** getting Top3 SHALL work correctly
- **AND** checking task membership in Top3 SHALL work correctly
- **AND** all operations SHALL maintain data consistency

## ADDED Requirements

### Requirement: P0 Bug Fix Verification Tests
The system SHALL include comprehensive tests to verify P0 bug fixes and prevent regression.

#### Scenario: Task completion empty body test
- **GIVEN** a task exists and user is authenticated
- **WHEN** POST /tasks/{task_id}/complete is called without json body parameter
- **THEN** response status SHALL be 200
- **AND** response SHALL have UnifiedResponse format
- **AND** task.status SHALL be "completed"
- **AND** mood_feedback SHALL be None or not present
- **AND** completion_result SHALL show points granted

#### Scenario: Task completion with mood feedback test
- **GIVEN** a task exists and user is authenticated
- **WHEN** POST /tasks/{task_id}/complete is called with mood_feedback
- **THEN** response status SHALL be 200
- **AND** response SHALL include the provided mood_feedback
- **AND** mood_feedback.comment SHALL match the provided value
- **AND** mood_feedback.difficulty SHALL match the provided value

#### Scenario: Top3 setting UUID handling test
- **GIVEN** a user has sufficient points (>=300) and 3 valid tasks
- **WHEN** POST /tasks/special/top3 is called with valid task IDs
- **THEN** response status SHALL be 200
- **AND** response SHALL NOT contain UUID-related errors
- **AND** points_consumed SHALL be 300
- **AND** remaining_balance SHALL be correctly calculated
- **AND** task_ids SHALL be stored correctly

#### Scenario: Top3 retrieval after setting test
- **GIVEN** Top3 has been successfully set
- **WHEN** GET /tasks/special/top3/{date} is called
- **THEN** response status SHALL be 200
- **AND** response SHALL contain the previously set task IDs
- **AND** response SHALL include creation timestamp
- **AND** no UUID errors SHALL occur during retrieval

### Requirement: Regression Prevention
The system SHALL include safeguards to prevent reintroduction of P0 bugs.

#### Scenario: Automated regression test suite
- **GIVEN** the P0 bug fixes are deployed
- **WHEN** any code changes are made to task or top3 domains
- **THEN** regression tests SHALL automatically run
- **AND** tests SHALL verify empty body task completion still works
- **AND** tests SHALL verify Top3 UUID handling still works
- **AND** any regression SHALL fail CI/CD pipeline

#### Scenario: Code review checklist for request body changes
- **GIVEN** a pull request modifies API endpoint definitions
- **WHEN** code review is performed
- **THEN** reviewers SHALL verify Body() parameter usage is correct
- **AND** reviewers SHALL check if optional bodies use Body(None)
- **AND** reviewers SHALL check if required bodies use Body(...)
- **AND** documentation SHALL be updated if behavior changes

#### Scenario: Code review checklist for UUID/string interactions
- **GIVEN** a pull request modifies service method calls
- **WHEN** code review is performed
- **THEN** reviewers SHALL verify type consistency at service boundaries
- **AND** reviewers SHALL check for explicit str(uuid) conversions
- **AND** reviewers SHALL flag raw UUID objects passed to string-expecting methods
- **AND** TODO comments SHALL reference Phase 2 comprehensive fix

## REMOVED Requirements
None. This spec only adds new requirements and modifies existing ones.

## Cross-Reference
- **Depends on**: real-http-testing (requires real HTTP test framework for verification)
- **Depended by**: None (bug fixes are independent)
- **Related to**: 1.4.2-uuid-type-safety-p1-fixes (Phase 2 will comprehensively address UUID/string type system)
