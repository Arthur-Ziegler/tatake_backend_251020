# performance-testing Specification

## Purpose
建立性能基准测试体系，确保所有API端点满足性能SLA，并检测性能回归。

## ADDED Requirements

### Requirement: Performance Measurement Infrastructure
The system SHALL provide performance tracking infrastructure to measure and compare API response times.

#### Scenario: Measure function execution time accurately
- **GIVEN** a function to be performance tested
- **WHEN** performance tracker measures the function
- **THEN** it SHALL use time.perf_counter() for high precision
- **AND** it SHALL convert time to milliseconds
- **AND** it SHALL record duration even if function raises exception
- **AND** it SHALL support multiple measurements for statistics

#### Scenario: Calculate performance statistics
- **GIVEN** multiple performance measurements are collected
- **WHEN** get_statistics() is called
- **THEN** it SHALL calculate P50 (median)
- **AND** it SHALL calculate P95 (95th percentile)
- **AND** it SHALL calculate P99 (99th percentile)
- **AND** it SHALL calculate min, max, mean values
- **AND** it SHALL include sample count and timestamp

#### Scenario: Store and load performance baseline
- **GIVEN** performance statistics for an endpoint
- **WHEN** baseline is saved for first time
- **THEN** statistics SHALL be written to JSON file
- **AND** file SHALL be stored in tests/reports/performance_baseline.json
- **WHEN** baseline is loaded later
- **THEN** previously saved statistics SHALL be returned
- **AND** missing endpoints SHALL return empty dict not error

#### Scenario: Compare with baseline and detect regression
- **GIVEN** current performance stats and historical baseline
- **WHEN** comparison is performed
- **THEN** it SHALL calculate P95 difference
- **AND** it SHALL calculate regression percentage
- **AND** regression SHALL be flagged if P95 > baseline * 1.2 (20% threshold)
- **AND** result SHALL include status: "ok", "regression", or "baseline_created"

### Requirement: API Response Time Performance Tests
All major API endpoints SHALL meet performance SLA with P95 < 200ms, P99 < 500ms.

#### Scenario: Tasks list API performance
- **GIVEN** user has 100 tasks in database
- **WHEN** GET /tasks is called 20 times
- **THEN** P95 response time SHALL be < 200ms
- **AND** P99 response time SHALL be < 500ms
- **AND** no single request SHALL timeout
- **AND** performance SHALL compare favorably with baseline

#### Scenario: Task creation API performance
- **GIVEN** authenticated user
- **WHEN** POST /tasks/create is called 20 times
- **THEN** P95 response time SHALL be < 200ms
- **AND** all tasks SHALL be created successfully
- **AND** database writes SHALL complete within SLA

#### Scenario: Task completion API performance
- **GIVEN** user has 50 active tasks
- **WHEN** PATCH /tasks/{task_id}/complete is called 20 times
- **THEN** P95 response time SHALL be < 200ms
- **AND** completion logic (check Top3, award points) SHALL execute efficiently

#### Scenario: Points balance API performance
- **GIVEN** user has 200 points transactions
- **WHEN** GET /points/my-points is called 20 times
- **THEN** P95 response time SHALL be < 200ms
- **AND** balance calculation (SUM query) SHALL be optimized
- **AND** response SHALL be consistent across all requests

#### Scenario: Points transactions API performance with pagination
- **GIVEN** user has 200 transactions
- **WHEN** GET /points/transactions is called with limit=20
- **THEN** P95 response time SHALL be < 200ms
- **AND** pagination SHALL use efficient LIMIT/OFFSET query
- **AND** response SHALL include correct page of transactions

#### Scenario: Rewards retrieval API performance
- **GIVEN** user has 10 different reward types
- **WHEN** GET /rewards/my-rewards is called 20 times
- **THEN** P95 response time SHALL be < 200ms
- **AND** reward aggregation query SHALL be optimized
- **AND** response SHALL correctly group by reward_id

#### Scenario: Top3 set API performance
- **GIVEN** user has sufficient points and tasks
- **WHEN** POST /top3/set is called 20 times (different dates)
- **THEN** P95 response time SHALL be < 200ms
- **AND** transaction (check balance, deduct points, create record) SHALL be atomic and fast

#### Scenario: Chat message API performance
- **GIVEN** active chat session
- **WHEN** POST /chat/message is called 10 times
- **THEN** P95 response time SHALL be < 500ms (higher SLA for AI processing)
- **AND** message storage SHALL be fast
- **AND** AI response generation SHALL not block excessively

### Requirement: Database Query Performance Analysis
Database queries SHALL be optimized to prevent N+1 queries and slow operations.

#### Scenario: Detect N+1 query problems
- **GIVEN** API endpoint that loads related data
- **WHEN** performance test runs with query logging enabled
- **THEN** test SHALL count number of database queries
- **AND** test SHALL flag endpoints with excessive queries (>10 for single request)
- **AND** test SHALL suggest using eager loading (selectinload/joinedload)

#### Scenario: Index usage verification
- **GIVEN** database tables with indexes on user_id, created_at
- **WHEN** performance test queries are analyzed
- **THEN** queries SHALL use indexes (not full table scan)
- **AND** EXPLAIN ANALYZE SHALL show index usage
- **AND** query execution time SHALL be logarithmic not linear

#### Scenario: Transaction performance
- **GIVEN** operations requiring transactions (points deduction)
- **WHEN** transaction performance is measured
- **THEN** transaction lock time SHALL be minimal
- **AND** transaction SHALL commit within 50ms
- **AND** concurrent transactions SHALL not cause deadlocks

### Requirement: Performance Regression Detection
The system SHALL automatically detect performance regressions in CI/CD pipeline.

#### Scenario: Detect P95 regression beyond threshold
- **GIVEN** historical baseline shows P95=100ms
- **WHEN** current test measures P95=150ms (50% increase)
- **THEN** comparison SHALL flag regression
- **AND** test SHALL fail with detailed diff
- **AND** message SHALL show "P95 increased by 50ms (50%)"

#### Scenario: Allow minor performance variations
- **GIVEN** historical baseline shows P95=100ms
- **WHEN** current test measures P95=110ms (10% increase)
- **THEN** comparison SHALL NOT flag regression (within 20% threshold)
- **AND** test SHALL pass
- **AND** message SHALL show "performance ok"

#### Scenario: Update baseline after intentional optimization
- **GIVEN** code optimization reduces P95 from 150ms to 80ms
- **WHEN** performance test runs with --update-baseline flag
- **THEN** new baseline SHALL be saved
- **AND** future tests SHALL compare against new 80ms baseline
- **AND** baseline file SHALL include timestamp of update

### Requirement: Performance Reporting
Performance test results SHALL be aggregated into comprehensive reports.

#### Scenario: Generate performance summary report
- **GIVEN** all performance tests have run
- **WHEN** report generator aggregates results
- **THEN** report SHALL list all tested endpoints
- **AND** report SHALL show P50/P95/P99 for each endpoint
- **AND** report SHALL highlight endpoints exceeding SLA
- **AND** report SHALL show comparison with baseline

#### Scenario: Export performance data for monitoring
- **GIVEN** performance statistics are collected
- **WHEN** data is exported
- **THEN** data SHALL be in JSON format
- **AND** data SHALL include timestamp, endpoint, statistics
- **AND** data SHALL be importable to monitoring tools (Grafana, etc)

## Cross-Reference
- **Depends on**:
  - 1.4.1-real-http-testing-framework-p0-fixes (requires real HTTP server)
  - 1.4.2-uuid-type-safety-p1-fixes (requires stable code base)
- **Modifies**:
  - api-testing (adds performance test suite)
- **Depended by**: None
