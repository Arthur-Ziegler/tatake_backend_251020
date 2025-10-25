# uuid-type-system Specification

## Purpose
建立统一的UUID类型系统，定义清晰的类型边界和转换规则，消除系统中UUID/str混用导致的运行时错误。

## ADDED Requirements

### Requirement: UUID Type Conversion Utility Library
The system SHALL provide a centralized UUID type conversion utility library with comprehensive error handling.

#### Scenario: Convert string to UUID with validation
- **GIVEN** a string value that may or may not be a valid UUID format
- **WHEN** ensure_uuid(value) is called
- **THEN** it SHALL return UUID object if value is valid UUID string
- **AND** it SHALL return the original UUID if value is already UUID object
- **AND** it SHALL return None if value is None
- **AND** it SHALL raise ValueError with clear message if value is invalid UUID format
- **AND** it SHALL raise TypeError if value is neither str nor UUID nor None

#### Scenario: Convert UUID to string with validation
- **GIVEN** a UUID object or string value
- **WHEN** ensure_str(value) is called
- **THEN** it SHALL return string representation if value is UUID object
- **AND** it SHALL validate and return string if value is already valid UUID string
- **AND** it SHALL return None if value is None
- **AND** it SHALL raise ValueError if string value is not valid UUID format
- **AND** it SHALL raise TypeError if value is neither str nor UUID nor None

#### Scenario: Convert list of UUIDs to strings
- **GIVEN** a list containing UUID objects and/or strings
- **WHEN** uuid_list_to_str(uuids) is called
- **THEN** it SHALL convert all elements to strings
- **AND** it SHALL validate each element is valid UUID
- **AND** it SHALL raise ValueError for any invalid UUID in the list

#### Scenario: Convert list of strings to UUIDs
- **GIVEN** a list containing valid UUID strings
- **WHEN** str_list_to_uuid(strings) is called
- **THEN** it SHALL convert all strings to UUID objects
- **AND** it SHALL validate each string is valid UUID format
- **AND** it SHALL raise ValueError for any invalid UUID string

### Requirement: Three-Layer UUID Type Boundary System
The system SHALL enforce UUID type boundaries at API, Business, and Database layers with explicit conversion points.

#### Scenario: API layer automatic UUID conversion for path parameters
- **GIVEN** an API endpoint with UUID path parameter
- **WHEN** the endpoint is defined using FastAPI
- **THEN** path parameter SHALL be annotated with UUID type
- **AND** FastAPI SHALL automatically convert string to UUID
- **AND** invalid UUID strings SHALL result in 422 validation error
- **AND** the converted UUID SHALL be passed to business logic

#### Scenario: API layer explicit UUID conversion for request bodies
- **GIVEN** an API endpoint accepting UUID in JSON request body
- **WHEN** the request is processed
- **THEN** JSON SHALL contain UUID as string (JSON limitation)
- **AND** Schema SHALL define field as Optional[str]
- **AND** API handler SHALL explicitly convert string to UUID using ensure_uuid()
- **AND** the converted UUID SHALL be passed to service layer

#### Scenario: Business layer exclusive UUID usage
- **GIVEN** any service or repository method
- **WHEN** the method processes user IDs, task IDs, or any entity IDs
- **THEN** all parameters SHALL be typed as UUID
- **AND** all internal variables SHALL use UUID type
- **AND** all method signatures SHALL explicitly declare Union[str, UUID] if accepting both
- **AND** first action SHALL be converting to UUID using ensure_uuid()

#### Scenario: Database layer UUID to string conversion for storage
- **GIVEN** a domain model needs to be persisted to database
- **WHEN** repository layer prepares data for insertion/update
- **THEN** all UUID fields SHALL be converted to strings using ensure_str()
- **AND** database columns SHALL be VARCHAR type
- **AND** conversion SHALL happen in repository layer, not service layer

#### Scenario: Database layer string to UUID conversion for retrieval
- **GIVEN** data is retrieved from database
- **WHEN** repository layer constructs domain objects
- **THEN** all ID string fields SHALL be converted to UUID using ensure_uuid()
- **AND** domain objects SHALL contain UUID-typed fields
- **AND** conversion SHALL happen in repository layer

### Requirement: Comprehensive Type Annotations for UUID Fields
The system SHALL provide 100% type annotation coverage for all UUID-related code.

#### Scenario: Service method UUID type annotations
- **GIVEN** any service class method that accepts user_id or entity IDs
- **WHEN** the method signature is defined
- **THEN** parameters SHALL be annotated as Union[str, UUID] if both types accepted
- **AND** parameters SHALL be annotated as UUID if only UUID accepted
- **AND** return types SHALL be explicitly annotated
- **AND** docstrings SHALL document UUID handling behavior

#### Scenario: Repository method UUID type annotations
- **GIVEN** any repository class method
- **WHEN** the method interacts with database
- **THEN** input parameters SHALL be annotated with UUID or Union[str, UUID]
- **AND** database query variables SHALL use str type after conversion
- **AND** return types SHALL use UUID type for domain objects
- **AND** all conversions SHALL be explicitly visible in code

#### Scenario: Type checker validation
- **GIVEN** the codebase with UUID type annotations
- **WHEN** mypy type checker is run with --strict flag
- **THEN** it SHALL pass without UUID-related type errors
- **AND** it SHALL detect any unsafe UUID usage
- **AND** it SHALL validate all conversions are type-safe

## MODIFIED Requirements

### Requirement: Points Service UUID Handling (from points domain)
**Modification**: All Points Service methods SHALL accept Union[str, UUID] and internally convert to appropriate type for each layer.

#### Scenario: Get balance with UUID type flexibility
- **GIVEN** a caller (API or service) needs to get user points balance
- **WHEN** points_service.get_balance(user_id) is called
- **THEN** it SHALL accept both str and UUID for user_id parameter
- **AND** it SHALL use ensure_str() to convert to string for database query
- **AND** it SHALL maintain backward compatibility with existing callers
- **AND** it SHALL log the user_id for debugging purposes

### Requirement: Reward Service UUID Handling (from reward domain)
**Modification**: All Reward Service methods SHALL enforce UUID type safety throughout the call chain.

#### Scenario: Get user rewards with UUID conversion
- **GIVEN** a user wants to retrieve their rewards
- **WHEN** reward_service.get_my_rewards(user_id) is called
- **THEN** it SHALL convert user_id to string for database query
- **AND** it SHALL handle empty results gracefully
- **AND** it SHALL log query parameters for debugging
- **AND** it SHALL return typed response with consistent structure

## Cross-Reference
- **Depends on**: 1.4.1-real-http-testing-framework-p0-fixes (Phase 1 testing infrastructure)
- **Depended by**: 1.4.3-api-coverage-quality-assurance (Phase 3 will build on type-safe foundation)
- **Modifies**: api-testing (all tests must use UUID-aware assertions)
