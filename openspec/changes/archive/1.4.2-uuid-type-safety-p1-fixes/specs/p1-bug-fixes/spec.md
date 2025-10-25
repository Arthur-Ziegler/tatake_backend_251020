# p1-bug-fixes Specification

## Purpose
修复P1级bug，确保积分、奖励、用户管理功能正常可用，并删除不需要的avatar和feedback功能。

## MODIFIED Requirements

### Requirement: Points API Endpoints Consistency
The Points API SHALL provide consistent and correctly documented endpoints matching v3 specification.

#### Scenario: Get points balance via correct endpoint
- **GIVEN** a user wants to check their points balance
- **WHEN** GET /points/my-points is called with valid auth token
- **THEN** response status SHALL be 200
- **AND** response SHALL contain current_balance field
- **AND** response SHALL contain total_earned and total_spent statistics
- **AND** UUID type handling SHALL work correctly without errors

#### Scenario: Get points transactions history
- **GIVEN** a user wants to view their points transaction history
- **WHEN** GET /points/transactions is called with pagination parameters
- **THEN** response status SHALL be 200
- **AND** response SHALL contain array of transactions
- **AND** each transaction SHALL have id, amount, source, created_at fields
- **AND** pagination SHALL work correctly
- **AND** UUID filtering SHALL work correctly

#### Scenario: Incorrect API paths SHALL be removed
- **GIVEN** the codebase may have incorrect API path definitions
- **WHEN** code review is performed
- **THEN** /points/balance endpoint SHALL NOT exist (incorrect path)
- **AND** only /points/my-points SHALL exist for balance query
- **AND** API documentation SHALL reflect correct paths only

### Requirement: Reward System Data Persistence and Retrieval
The Reward System SHALL ensure data is correctly persisted and retrievable with proper UUID handling.

#### Scenario: Welcome gift claim with persistence verification
- **GIVEN** a new user claims welcome gift
- **WHEN** POST /user/welcome-gift/claim is called
- **THEN** the system SHALL write 1000 points to points_transactions table
- **AND** the system SHALL write 3 reward items to user_rewards table
- **AND** the system SHALL flush changes within the transaction
- **AND** the system SHALL verify write succeeded by querying count
- **AND** the system SHALL commit transaction only if verification passes
- **AND** the system SHALL rollback and raise exception if verification fails

#### Scenario: Reward retrieval with UUID type handling
- **GIVEN** a user has claimed welcome gift or earned rewards
- **WHEN** GET /rewards/my-rewards is called
- **THEN** user_id SHALL be converted to string for database query
- **AND** query SHALL correctly match user_id in database
- **AND** empty results SHALL return {rewards: {}, total_types: 0}
- **AND** non-empty results SHALL return properly structured rewards dict
- **AND** no UUID-related errors SHALL occur

#### Scenario: Reward query logging for debugging
- **GIVEN** reward system processes any query
- **WHEN** database operations are performed
- **THEN** system SHALL log user_id being queried
- **AND** system SHALL log number of results found
- **AND** system SHALL log any conversion operations
- **AND** logs SHALL be at INFO level for normal operations
- **AND** logs SHALL be at WARNING level for empty results

### Requirement: User Management Session Dependency Unification
The User Management domain SHALL use standard SessionDep dependency consistent with other domains.

#### Scenario: User profile retrieval with standard session
- **GIVEN** a user wants to retrieve their profile
- **WHEN** GET /user/profile is called
- **THEN** endpoint SHALL use SessionDep not get_user_session
- **AND** user_id SHALL be converted to string for database lookup
- **AND** Auth model SHALL be queried with session.get()
- **AND** response SHALL return 404 if user not found
- **AND** response SHALL return 200 with user data if found

#### Scenario: User profile update with UUID handling
- **GIVEN** a user wants to update their profile
- **WHEN** PUT /user/profile is called with update data
- **THEN** user_id SHALL be converted to string for database lookup
- **AND** updates SHALL be applied to Auth model
- **AND** session.commit() SHALL persist changes
- **AND** response SHALL include updated fields list

#### Scenario: get_user_session dependency removal
- **GIVEN** the codebase contains get_user_session function
- **WHEN** migration to standard SessionDep is complete
- **THEN** src/domains/user/database.py file SHALL be deleted
- **AND** all imports of get_user_session SHALL be removed
- **AND** all user router endpoints SHALL use SessionDep
- **AND** grep for "get_user_session" SHALL return zero results

## REMOVED Requirements

### Requirement: Avatar Upload Functionality
The Avatar Upload feature SHALL be completely removed from the system.

#### Scenario: Avatar upload endpoint removal
- **GIVEN** the codebase may contain avatar upload endpoint
- **WHEN** cleanup is complete
- **THEN** POST /user/avatar endpoint SHALL NOT exist
- **AND** AvatarUploadResponse schema SHALL be deleted
- **AND** all imports of AvatarUploadResponse SHALL be removed
- **AND** upload_avatar function SHALL be deleted

#### Scenario: Avatar database field removal
- **GIVEN** Auth table may have avatar column
- **WHEN** database migration is applied
- **THEN** avatar column SHALL be dropped from auth table
- **AND** migration SHALL be reversible (downgrade re-adds column as nullable)
- **AND** no code SHALL reference auth.avatar field

### Requirement: Feedback Submission Functionality
The Feedback feature SHALL be completely removed from the system.

#### Scenario: Feedback submission endpoint removal
- **GIVEN** the codebase may contain feedback endpoints
- **WHEN** cleanup is complete
- **THEN** POST /user/feedback endpoint SHALL NOT exist
- **AND** FeedbackRequest schema SHALL be deleted
- **AND** FeedbackSubmitResponse schema SHALL be deleted
- **AND** submit_feedback function SHALL be deleted

#### Scenario: Feedback database table removal
- **GIVEN** database may have feedback table
- **WHEN** database migration is applied
- **THEN** feedback table SHALL be dropped if it exists
- **AND** migration SHALL handle case where table doesn't exist
- **AND** no code SHALL reference feedback table

## ADDED Requirements

### Requirement: P1 Bug Fix Verification Tests
The system SHALL include comprehensive tests to verify all P1 bugs are fixed and prevent regression.

#### Scenario: Points balance API test
- **GIVEN** a user with known points balance
- **WHEN** GET /points/my-points is called
- **THEN** response SHALL return correct balance
- **AND** response SHALL have proper UnifiedResponse format
- **AND** no UUID errors SHALL occur
- **AND** test SHALL use real HTTP request not ASGI transport

#### Scenario: Points transactions API test
- **GIVEN** a user with transaction history
- **WHEN** GET /points/transactions is called
- **THEN** response SHALL return transaction list
- **AND** each transaction SHALL have correct user_id
- **AND** pagination SHALL work correctly
- **AND** no UUID errors SHALL occur

#### Scenario: Reward retrieval after welcome gift test
- **GIVEN** a user has claimed welcome gift
- **WHEN** GET /rewards/my-rewards is called
- **THEN** response SHALL contain the 3 welcome gift reward items
- **AND** quantities SHALL match expected values (3, 10, 5)
- **AND** reward names SHALL be correct
- **AND** no UUID errors SHALL occur

#### Scenario: User profile CRUD operations test
- **GIVEN** an authenticated user
- **WHEN** GET /user/profile and PUT /user/profile are called
- **THEN** both operations SHALL succeed
- **AND** user data SHALL be correctly retrieved and updated
- **AND** no session dependency errors SHALL occur
- **AND** no UUID errors SHALL occur

#### Scenario: Deleted functionality verification test
- **GIVEN** avatar and feedback features are removed
- **WHEN** POST /user/avatar and POST /user/feedback are called
- **THEN** both SHALL return 404 Not Found
- **AND** OpenAPI documentation SHALL NOT include these endpoints
- **AND** no code references to these features SHALL exist

## Cross-Reference
- **Depends on**:
  - 1.4.1-real-http-testing-framework-p0-fixes (requires real HTTP testing)
  - uuid-type-system (requires UUID conversion utilities)
- **Modifies**:
  - api-testing (points and rewards tests updated)
  - welcome-gift (persistence verification added)
- **Depended by**: 1.4.3-api-coverage-quality-assurance (Phase 3 comprehensive testing)
