# HTPI Admin Portal Architecture

## Overview

The Admin Portal is a **thin MVC layer** with NO business logic. It acts as a bridge between:
- **Frontend**: Socket.IO events from the browser
- **Backend**: NATS messages to/from microservices

## Architecture Flow

```
Browser → Socket.IO → Admin Portal → NATS → Microservices → MongoDB
                           ↑                        ↓
                           ← ← ← ← ← ← ← ← ← ← ← ← ←
```

## Key Principles

1. **NO Business Logic** in the portal:
   - No ID generation
   - No data validation
   - No calculations
   - No data transformation (except adding auth context)

2. **Pure Message Forwarding**:
   - Receive Socket.IO event
   - Add authentication context
   - Publish to NATS
   - Wait for NATS response
   - Emit Socket.IO response

3. **Microservices Handle Everything**:
   - ID generation
   - Data validation
   - Business rules
   - MongoDB operations (via mongodb service)
   - ClaimMD API calls

## Example Flow: Creating a Patient

### 1. Browser sends Socket.IO event:
```javascript
socket.emit('admin:patients:create', {
    firstName: 'John',
    lastName: 'Doe',
    tenantId: 'tenant-001',
    requestId: 'req-123'
});
```

### 2. Admin Portal forwards to NATS:
```python
@socketio.on('admin:patients:create')
def handle_create_patient(data):
    # Only add context, NO business logic
    nats_message = {
        **data,
        'createdBy': client['user']['id'],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Publish to NATS
    publish_to_nats('patient.create', nats_message)
```

### 3. Patient Service (separate microservice) handles it:
```python
# In htpi-patient-service
async def handle_create_patient(msg):
    data = json.loads(msg.data.decode())
    
    # Business logic HERE, not in portal
    patient = {
        'id': generate_patient_id(),  # Service generates ID
        'patientId': f"P{random.randint(100000, 999999)}",
        'firstName': validate_name(data['firstName']),
        'lastName': validate_name(data['lastName']),
        'createdAt': datetime.utcnow(),
        'createdBy': data['createdBy']
    }
    
    # Save via MongoDB service
    await publish('mongodb.patients.insert', patient)
    
    # Respond back to admin portal
    await publish(f"admin.patients.response.{data['clientId']}", {
        'responseType': 'created',
        'requestId': data['requestId'],
        'patient': patient,
        'tenantId': data['tenantId']
    })
```

### 4. Admin Portal receives NATS response and emits to browser:
```python
async def handle_patient_response(msg):
    data = json.loads(msg.data.decode())
    
    # Just forward the response, no processing
    socketio.emit(f"admin:patients:create:response:{data['requestId']}", {
        'success': True,
        'patient': data['patient']
    })
```

## NATS Subject Naming Convention

- **Requests**: `htpi.<service>.<action>`
  - `htpi.patient.create`
  - `htpi.insurance.eligibility.check`
  - `htpi.claims.submit`

- **Responses**: `admin.<service>.response.<client_id>`
  - `admin.patients.response.abc123`
  - `admin.claims.response.xyz789`

- **Broadcasts**: `admin.broadcast.<service>.<tenant_id>`
  - `admin.broadcast.patients.tenant-001`
  - `admin.broadcast.claims.tenant-002`

## Service Responsibilities

### Admin Portal (this service)
- Socket.IO connection management
- Authentication verification
- Session management
- Message forwarding

### Patient Service
- Patient ID generation
- Patient data validation
- Patient CRUD operations

### Insurance Service
- Insurance policy management
- ClaimMD eligibility checks
- Payer list management

### Claims Service
- Claim ID generation
- ClaimMD claim submission
- Claim status tracking
- ERA/remittance processing

### MongoDB Service
- All database operations
- Data persistence
- Query optimization

## Benefits of This Architecture

1. **Scalability**: Each service can scale independently
2. **Maintainability**: Business logic centralized in services
3. **Testability**: Services can be tested in isolation
4. **Flexibility**: Easy to add new services or modify existing ones
5. **Reliability**: If one service fails, others continue working

## Current Implementation Status

Currently, the portal has mock business logic because NATS is not available in sync mode. In production:
1. Remove ALL mock data generation
2. Remove ALL business logic
3. Implement proper async NATS request/reply
4. Let services handle everything

## Next Steps

1. Convert to async Flask/Socket.IO
2. Implement proper NATS request/reply pattern
3. Remove all business logic from portal
4. Create separate microservices for each domain
5. Implement MongoDB service for data persistence