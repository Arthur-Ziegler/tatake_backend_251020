# Task Router Migration Specification

## MODIFIED Requirements

### Requirement: Complete Microservice Proxy Implementation
The task router SHALL be completely refactored to act as a pure proxy to the microservice, removing all local business logic and database operations.

#### Scenario: Task creation proxy
- **GIVEN** a client calls POST /tasks with task creation data
- **WHEN** the router processes the request
- **THEN** it SHALL extract user_id from JWT token
- **AND** it SHALL validate task data (title, priority, due_date)
- **AND** it SHALL call the enhanced microservice client
- **AND** it SHALL return the microservice response directly
- **AND** it SHALL NOT perform any local database operations

#### Scenario: Task query proxy transformation
- **GIVEN** a client calls POST /tasks/query with pagination parameters
- **WHEN** the router processes the request
- **THEN** it SHALL extract user_id from request body
- **AND** it SHALL validate pagination parameters (page, page_size)
- **AND** it SHALL call microservice with GET /api/v1/tasks/{user_id}
- **AND** it SHALL transform microservice response to expected pagination format
- **AND** it SHALL handle both array and paginated response formats

#### Scenario: Single task operation proxy
- **GIVEN** a client calls PUT /tasks/{task_id} or DELETE /tasks/{task_id}
- **WHEN** the router processes the request
- **THEN** it SHALL extract user_id from JWT token and task_id from path
- **AND** it SHALL validate both UUIDs
- **AND** it SHALL call microservice with /api/v1/tasks/{user_id}/{task_id}
- **AND** it SHALL return the microservice response directly

### Requirement: Top3 Management Integration
The router SHALL integrate Top3 functionality completely with the microservice, including proper request/response handling.

#### Scenario: Top3 setting proxy
- **GIVEN** a client calls POST /tasks/special/top3 with date and task_ids
- **WHEN** the router processes the request
- **THEN** it SHALL extract user_id from JWT token
- **AND** it SHALL validate date format and task_id list
- **AND** it SHALL call microservice POST /api/v1/tasks/top3
- **AND** it SHALL return the microservice response directly
- **AND** it SHALL NOT perform local points deduction (handled by microservice)

#### Scenario: Top3 query proxy transformation
- **GIVEN** a client calls GET /tasks/special/top3/{date}
- **WHEN** the router processes the request
- **THEN** it SHALL extract user_id from JWT token and date from path
- **AND** it SHALL validate date format
- **AND** it SHALL call microservice GET /api/v1/tasks/top3/{user_id}/{date}
- **AND** it SHALL return the microservice response directly

### Requirement: Task Completion Integration
The router SHALL integrate task completion functionality with the microservice to leverage the built-in reward system.

#### Scenario: Task completion proxy
- **GIVEN** a client calls POST /tasks/{task_id}/complete with completion data
- **WHEN** the router processes the request
- **THEN** it SHALL extract user_id from JWT token and task_id from path
- **AND** it SHALL validate both UUIDs
- **AND** it SHALL call microservice POST /api/v1/tasks/{user_id}/{task_id}/complete
- **AND** it SHALL return the complete response including reward information
- **AND** it SHALL NOT perform any local reward calculations

### Requirement: Focus Status Integration
The router SHALL integrate focus status functionality with the microservice, replacing the local implementation.

#### Scenario: Focus status recording proxy
- **GIVEN** a client calls POST /tasks/focus-status with focus data
- **WHEN** the router processes the request
- **THEN** it SHALL extract user_id from JWT token
- **AND** it SHALL validate focus_status, duration_minutes, and optional task_id
- **AND** it SHALL call microservice POST /api/v1/focus/sessions
- **AND** it SHALL return the microservice response directly
- **AND** it SHALL NOT perform any local database operations

### Requirement: Pomodoro Count Integration
The router SHALL integrate pomodoro count functionality with the microservice, replacing the local implementation.

#### Scenario: Pomodoro count query proxy
- **GIVEN** a client calls GET /tasks/pomodoro-count with date_filter parameter
- **WHEN** the router processes the request
- **THEN** it SHALL extract user_id from JWT token
- **AND** it SHALL validate date_filter parameter (today, week, month)
- **AND** it SHALL call microservice GET /api/v1/pomodoros/count with user_id and date_filter
- **AND** it SHALL return the microservice response directly
- **AND** it SHALL NOT perform any local database calculations

## REMOVED Requirements

### Requirement: Local Database Operations
The router SHALL NOT perform any local database operations for task management.

#### Scenario: No local task persistence
- **GIVEN** any task operation request
- **WHEN** the router processes the request
- **THEN** it SHALL NOT access the local database
- **AND** it SHALL NOT use any local repository classes
- **AND** it SHALL NOT perform any SQL queries

#### Scenario: No local model usage
- **GIVEN** any task operation request
- **WHEN** the router processes the request
- **THEN** it SHALL NOT use any local Task or Top3 model classes
- **AND** it SHALL NOT perform any model validation or transformations

### Requirement: Local Business Logic
The router SHALL NOT contain any local business logic for task operations.

#### Scenario: No local validation logic
- **GIVEN** any task operation request
- **WHEN** the router processes the request
- **THEN** it SHALL NOT perform any business rule validation
- **AND** it SHALL delegate all validation to the microservice
- **AND** it SHALL only perform basic API contract validation

#### Scenario: No local calculations
- **GIVEN** any calculation request (pomodoro count, completion rewards)
- **WHEN** the router processes the request
- **THEN** it SHALL NOT perform any local calculations
- **AND** it SHALL delegate all calculations to the microservice

## ADDED Requirements

### Requirement: Request Validation Enhancement
The router SHALL enhance request validation to ensure compatibility with microservice expectations.

#### Scenario: UUID format validation in router
- **GIVEN** any request containing user_id or task_id
- **WHEN** the router processes the request
- **THEN** it SHALL validate UUID format before calling microservice
- **AND** it SHALL return HTTP 400 for invalid UUID formats
- **AND** it SHALL provide clear error messages for UUID validation failures

#### Scenario: Priority format adaptation
- **GIVEN** a task creation or update request with priority parameter
- **WHEN** the router processes the request
- **THEN** it SHALL convert priority from lowercase ("low", "medium", "high") to titlecase ("Low", "Medium", "High")
- **AND** it SHALL validate that priority is one of the allowed values

#### Scenario: Date format validation
- **GIVEN** any request containing date parameters
- **WHEN** the router processes the request
- **THEN** it SHALL validate date format (YYYY-MM-DD)
- **AND** it SHALL validate that date is not in the past for certain operations
- **AND** it SHALL return HTTP 400 for invalid date formats

### Requirement: Response Adaptation
The router SHALL adapt microservice responses to match expected client formats while preserving data integrity.

#### Scenario: Task list response adaptation
- **GIVEN** a microservice returns task list in array format
- **WHEN** the router processes the response
- **THEN** it SHALL wrap the array in pagination structure
- **AND** it SHALL calculate pagination metadata (total_count, current_page, etc.)
- **AND** it SHALL maintain backward compatibility with existing client expectations

#### Scenario: Task detail response adaptation
- **GIVEN** a microservice returns task detail with different field names
- **WHEN** the router processes the response
- **THEN** it SHALL map field names to match expected client format
- **AND** it SHALL preserve all data values and types
- **AND** it SHALL handle missing fields gracefully

### Requirement: Error Handling Enhancement
The router SHALL provide enhanced error handling that distinguishes between client errors and microservice errors.

#### Scenario: Microservice error propagation
- **GIVEN** a microservice returns an error response
- **WHEN** the router receives the error
- **THEN** it SHALL preserve the original error code and message
- **AND** it SHALL add contextual information about the operation
- **AND** it SHALL log the error for debugging purposes

#### Scenario: Network error handling
- **GIVEN** a network error occurs while calling microservice
- **WHEN** the router catches the error
- **THEN** it SHALL return HTTP 503 Service Unavailable
- **AND** it SHALL provide a user-friendly error message
- **AND** it SHALL log the technical error details

### Requirement: Request Context Enhancement
The router SHALL enhance request context handling to support better debugging and monitoring.

#### Scenario: Request ID propagation
- **GIVEN** any incoming request
- **WHEN** the router processes the request
- **THEN** it SHALL generate or extract a request ID
- **AND** it SHALL include the request ID in microservice calls
- **AND** it SHALL include the request ID in response headers
- **AND** it SHALL log the request ID for traceability

#### Scenario: User context validation
- **GIVEN** any incoming request
- **WHEN** the router processes the request
- **THEN** it SHALL validate JWT token and extract user context
- **AND** it SHALL verify user is active and authorized
- **AND** it SHALL include user context in logs and microservice calls