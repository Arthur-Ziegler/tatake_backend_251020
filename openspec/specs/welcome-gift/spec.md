# welcome-gift Specification

## Purpose
TBD - created by archiving change 1.3-user-welcome-gift-and-api-testing. Update Purpose after archive.
## Requirements
### Requirement: Welcome Gift System
The system SHALL provide a welcome gift API endpoint that grants users 1000 points and a fixed set of rewards for testing purposes.

#### Scenario: User claims welcome gift successfully
- **WHEN** an authenticated user sends POST request to `/user/welcome-gift/claim`
- **THEN** the system SHALL add 1000 points to the user's balance with source_type `welcome_gift`
- **AND** the system SHALL add 3 point bonus cards (+50% points, 1 hour duration) to the user's rewards
- **AND** the system SHALL add 10 focus items (instant focus session completion) to the user's rewards
- **AND** the system SHALL add 5 time management coupons (extend task deadline by 1 day) to the user's rewards
- **AND** the system SHALL return a UnifiedResponse with code 200 containing the gift details

#### Scenario: User claims welcome gift multiple times
- **WHEN** a user sends multiple POST requests to `/user/welcome-gift/claim`
- **THEN** the system SHALL process each request successfully
- **AND** the system SHALL add the full gift package for each request
- **AND** the user's points balance SHALL increase by 1000 for each request
- **AND** the user SHALL receive the full set of rewards for each request

#### Scenario: Unauthenticated user attempts to claim gift
- **WHEN** an unauthenticated user sends POST request to `/user/welcome-gift/claim`
- **THEN** the system SHALL return UnifiedResponse with code 401
- **AND** the system SHALL include error message indicating authentication required

### Requirement: Welcome Gift Data Model Extension
The system SHALL extend existing transaction models to support welcome gift source type.

#### Scenario: Points transaction with welcome gift type
- **WHEN** welcome gift is claimed
- **THEN** the points_transactions record SHALL have source_type = 'welcome_gift'
- **AND** the amount SHALL be 1000
- **AND** the source_id SHALL reference the gift claim transaction

#### Scenario: Reward transaction with welcome gift type
- **WHEN** welcome gift rewards are granted
- **THEN** the reward_transactions records SHALL have source_type = 'welcome_gift'
- **AND** the quantity SHALL match the gift specification (3, 10, 5 respectively)
- **AND** the source_id SHALL reference the same gift claim transaction

### Requirement: Welcome Gift Reward Items
The system SHALL create and manage specific reward items for the welcome gift package.

#### Scenario: Initialize welcome gift rewards
- **WHEN** the system starts up
- **THEN** the system SHALL create point bonus card reward with name "积分加成卡"
- **AND** the system SHALL create focus item reward with name "专注道具"
- **AND** the system SHALL create time management coupon reward with name "时间管理券"
- **AND** all rewards SHALL be marked as active and available

