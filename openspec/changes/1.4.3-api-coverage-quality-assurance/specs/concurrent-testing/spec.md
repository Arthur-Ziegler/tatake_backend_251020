# concurrent-testing Specification

## Purpose
验证系统在并发场景下的数据一致性、事务隔离和性能稳定性，确保多用户并发操作不会导致数据错误。

## ADDED Requirements

### Requirement: Concurrent Testing Infrastructure
The system SHALL provide asyncio-based concurrent testing tools to simulate real concurrent user operations.

#### Scenario: Execute concurrent HTTP requests with asyncio
- **GIVEN** multiple HTTP requests to be executed concurrently
- **WHEN** concurrent tester runs with asyncio.gather()
- **THEN** all requests SHALL execute truly concurrently (not sequential)
- **AND** each request SHALL use separate httpx.AsyncClient
- **AND** each request SHALL record start time, duration, status
- **AND** exceptions SHALL be caught and recorded not propagated

#### Scenario: Aggregate concurrent test results
- **GIVEN** N concurrent requests have completed
- **WHEN** results are aggregated
- **THEN** success_count and error_count SHALL be calculated
- **AND** status code distribution SHALL be counted (200: X, 422: Y, etc)
- **AND** error messages SHALL be collected in list
- **AND** latency statistics SHALL be calculated (P50, P95, max)

#### Scenario: Support mixed concurrent scenarios
- **GIVEN** multiple different operations to run concurrently
- **WHEN** run_concurrent_scenarios() is called
- **THEN** each scenario SHALL execute its requests concurrently
- **AND** scenarios SHALL run in parallel with each other
- **AND** results SHALL be returned as list matching scenario order

### Requirement: Points System Concurrent Consistency
The Points system SHALL maintain data consistency under concurrent operations.

#### Scenario: Concurrent points deduction with balance check
- **GIVEN** user has 3000 points balance
- **WHEN** 10 concurrent requests deduct 300 points each
- **THEN** maximum 10 requests SHALL succeed (3000/300=10)
- **AND** some requests MAY fail with "insufficient points" error
- **AND** final balance SHALL equal 3000 - (success_count * 300)
- **AND** NO requests SHALL succeed if balance is insufficient (atomicity)

#### Scenario: Concurrent points addition consistency
- **GIVEN** user starts with 1000 points
- **WHEN** 10 concurrent requests add 100 points each
- **THEN** all 10 requests SHALL succeed
- **AND** final balance SHALL equal 1000 + (10 * 100) = 2000
- **AND** NO points transactions SHALL be lost
- **AND** transaction count SHALL equal 10

#### Scenario: Mixed concurrent points operations
- **GIVEN** user has 2000 points
- **WHEN** 5 concurrent add operations (+100) and 5 deduct operations (-100) execute
- **THEN** all operations SHALL succeed
- **AND** final balance SHALL equal 2000 (additions cancel deductions)
- **AND** transaction history SHALL contain all 10 operations
- **AND** NO race conditions SHALL cause incorrect balance

#### Scenario: Points balance query during concurrent updates
- **GIVEN** concurrent points deduction operations are in progress
- **WHEN** GET /points/my-points is called during updates
- **THEN** returned balance SHALL be consistent snapshot
- **AND** balance SHALL equal sum of committed transactions (read committed isolation)
- **AND** NO dirty reads SHALL occur
- **AND** query SHALL not block deduction operations

### Requirement: Top3 System Concurrent Uniqueness
The Top3 system SHALL enforce uniqueness constraints under concurrent operations.

#### Scenario: Concurrent Top3 set for same date
- **GIVEN** user has not set Top3 for date X
- **WHEN** 3 concurrent requests try to set Top3 for date X
- **THEN** exactly 1 request SHALL succeed
- **AND** remaining 2 requests SHALL fail with "already set" error
- **AND** only 300 points SHALL be deducted (not 900)
- **AND** database SHALL contain exactly 1 Top3 record for date X

#### Scenario: Concurrent Top3 set for different dates
- **GIVEN** user has sufficient points (900+)
- **WHEN** 3 concurrent requests set Top3 for dates X, Y, Z
- **THEN** all 3 requests SHALL succeed
- **AND** 900 points SHALL be deducted total (300 each)
- **AND** database SHALL contain 3 separate Top3 records

#### Scenario: Concurrent Top3 query during creation
- **GIVEN** Top3 creation is in progress for date X
- **WHEN** GET /top3?date=X is called concurrently
- **THEN** query SHALL return empty or completed Top3 (not partial)
- **AND** query SHALL not see uncommitted transaction data
- **AND** query SHALL not block creation operation

### Requirement: Reward System Concurrent Idempotency
The Reward system SHALL ensure idempotent operations under concurrent requests.

#### Scenario: Concurrent welcome gift claim attempts
- **GIVEN** new user has not claimed welcome gift
- **WHEN** 5 concurrent requests claim welcome gift
- **THEN** exactly 1 request SHALL succeed
- **AND** remaining 4 requests SHALL fail with "already claimed" error
- **AND** exactly 1000 points SHALL be awarded (not 5000)
- **AND** exactly 3 reward items SHALL be created (not 15)

#### Scenario: Concurrent reward redemption
- **GIVEN** user has 5 "time_freeze" rewards
- **WHEN** 5 concurrent requests redeem "time_freeze" reward
- **THEN** all 5 requests SHALL succeed
- **AND** remaining quantity SHALL equal 0
- **AND** NO overdraft SHALL occur (negative quantity)

#### Scenario: Concurrent reward grant and query
- **GIVEN** reward grant operations are in progress
- **WHEN** GET /rewards/my-rewards is called concurrently
- **THEN** query SHALL return consistent snapshot of rewards
- **AND** query SHALL not see partial grant operations
- **AND** query SHALL not block grant operations

### Requirement: Task System Concurrent Operations
The Task system SHALL handle concurrent operations correctly.

#### Scenario: Concurrent task completion
- **GIVEN** user has 5 active tasks
- **WHEN** all 5 tasks are completed concurrently
- **THEN** all 5 requests SHALL succeed
- **AND** all 5 tasks SHALL have is_completed=true
- **AND** completion timestamps SHALL reflect actual completion order
- **AND** if tasks are in Top3, points SHALL be awarded correctly

#### Scenario: Concurrent task creation
- **GIVEN** authenticated user
- **WHEN** 10 tasks are created concurrently
- **THEN** all 10 requests SHALL succeed
- **AND** 10 distinct tasks SHALL exist in database
- **AND** each task SHALL have unique task_id (UUID collision check)
- **AND** all tasks SHALL be associated with correct user

#### Scenario: Concurrent task deletion and completion
- **GIVEN** 5 active tasks
- **WHEN** 3 tasks are being deleted and 2 are being completed concurrently
- **THEN** all operations SHALL succeed
- **AND** deleted tasks SHALL be marked is_deleted=true
- **AND** completed tasks SHALL be marked is_completed=true
- **AND** NO operations SHALL interfere with each other

### Requirement: Concurrent Load Performance
The system SHALL maintain acceptable performance under concurrent load.

#### Scenario: Concurrent load with 10 users
- **GIVEN** 10 concurrent users performing mixed operations
- **WHEN** each user performs 5 operations (task CRUD, points check)
- **THEN** all 50 operations SHALL complete within 10 seconds
- **AND** P95 latency SHALL remain < 500ms (degraded but acceptable)
- **AND** NO operations SHALL timeout
- **AND** system SHALL remain responsive

#### Scenario: Sustained concurrent load
- **GIVEN** continuous stream of concurrent requests
- **WHEN** load runs for 60 seconds with 5 concurrent users
- **THEN** throughput SHALL remain stable (no degradation over time)
- **AND** error rate SHALL remain < 5%
- **AND** memory usage SHALL not grow unboundedly (no leaks)
- **AND** database connection pool SHALL not exhaust

#### Scenario: Burst concurrent load
- **GIVEN** sudden spike of 20 concurrent requests
- **WHEN** burst occurs after idle period
- **THEN** all requests SHALL be processed (no rejections)
- **AND** P99 latency MAY spike temporarily but recover quickly
- **AND** system SHALL not crash or hang
- **AND** subsequent requests SHALL return to normal latency

### Requirement: Transaction Isolation and Deadlock Prevention
The system SHALL use appropriate transaction isolation levels and prevent deadlocks.

#### Scenario: Read committed isolation level
- **GIVEN** concurrent transactions modifying same user's data
- **WHEN** transaction A is in progress
- **THEN** transaction B SHALL see committed version of data (not dirty read)
- **AND** transaction B SHALL not block on transaction A's read locks
- **AND** both transactions SHALL eventually commit successfully

#### Scenario: Optimistic locking for concurrent updates
- **GIVEN** two transactions try to update same record
- **WHEN** both read initial value and compute new value
- **THEN** second transaction SHALL detect conflict
- **AND** second transaction SHALL retry or fail gracefully
- **AND** final state SHALL be consistent (one update wins)

#### Scenario: Deadlock detection and recovery
- **GIVEN** potential circular lock dependency exists
- **WHEN** concurrent transactions acquire locks in different order
- **THEN** database SHALL detect deadlock within 5 seconds
- **AND** one transaction SHALL be rolled back (deadlock victim)
- **AND** application SHALL retry rolled back transaction
- **AND** eventually all transactions SHALL succeed

## Cross-Reference
- **Depends on**:
  - 1.4.1-real-http-testing-framework-p0-fixes (requires real HTTP server)
  - 1.4.2-uuid-type-safety-p1-fixes (requires stable transaction code)
- **Modifies**:
  - api-testing (adds concurrent test suite)
- **Depended by**: None
