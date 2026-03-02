# Feeder Management API Documentation
## Mobile App Integration Guide

This documentation describes the REST API endpoints for the Feeder Management system, designed for mobile app integration.

---

## Base URL

All API endpoints are prefixed with: `/api/`

For example, if your server is running at `http://your-domain.com`, the complete URL would be:
```
http://your-domain.com/api/feeders/
```

---

## Authentication

Currently set to `AllowAny` for development. Update `permission_classes` in the `FeederViewSet` for production authentication.

---

## Available Endpoints

### 1. List All Feeders
**GET** `/api/feeders/`

Returns a paginated list of all feeders.

**Query Parameters:**
- `status` - Filter by status (pending, accepted, key_uploaded, rejected, under_process)
- `branch_id` - Filter by branch ID
- `district` - Filter by district (partial match)
- `search` - Search by name, software, or contact person

**Example Request:**
```bash
GET /api/feeders/?status=pending&search=supermarket
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "name": "ABC Supermarket",
    "address": "123 Main Street",
    "location": "Downtown",
    "area": "Central",
    "district": "District 1",
    "state": "Kerala",
    "contact_person": "John Doe",
    "contact_number": "1234567890",
    "email": "john@example.com",
    "reputed_person_name": "Jane Doe",
    "reputed_person_number": "0987654321",
    "software": "POS System",
    "nature": "supermarket",
    "branch": 1,
    "branch_name": "Main Branch",
    "no_of_system": 5,
    "pincode": "123456",
    "country": "India",
    "installation_date": "2026-02-25",
    "installation_date_formatted": "25/02/2026",
    "remarks": "Initial setup required",
    "software_amount": "50000.00",
    "module_charges": "10000.00",
    "modules": "Sales, Inventory",
    "modules_list": ["Sales", "Inventory"],
    "more_modules": "Reports, Analytics",
    "more_modules_list": ["Reports", "Analytics"],
    "module_prices": {"Reports": 5000, "Analytics": 5000},
    "status": "pending",
    "status_display": "Pending",
    "nature_display": "Supermarket",
    "status_class": "status-pending"
  }
]
```

---

### 2. Create New Feeder
**POST** `/api/feeders/`

Creates a new feeder entry.

**Request Body:**
```json
{
  "name": "XYZ Restaurant",
  "address": "456 Park Avenue",
  "location": "Uptown",
  "area": "North",
  "district": "District 2",
  "state": "Kerala",
  "contact_person": "Alice Smith",
  "contact_number": "5551234567",
  "email": "alice@example.com",
  "reputed_person_name": "Bob Smith",
  "reputed_person_number": "5559876543",
  "software": "Restaurant Management",
  "nature": "restaurant",
  "branch": 1,
  "no_of_system": 3,
  "pincode": "654321",
  "country": "India",
  "installation_date": "2026-03-01",
  "remarks": "Urgent installation",
  "software_amount": "75000.00",
  "module_charges": "15000.00",
  "modules": "Kitchen Display, Billing",
  "more_modules": "Online Ordering",
  "module_prices": {"Online Ordering": 15000}
}
```

**Response (201 Created):**
```json
{
  "id": 2,
  "name": "XYZ Restaurant",
  ...rest of the feeder data
}
```

**Validation Errors (400 Bad Request):**
```json
{
  "field_name": ["Error message"]
}
```

---

### 3. Retrieve Single Feeder
**GET** `/api/feeders/{id}/`

Returns details of a specific feeder.

**Example Request:**
```bash
GET /api/feeders/1/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "ABC Supermarket",
  ...complete feeder data
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Not found."
}
```

---

### 4. Update Feeder (Full Update)
**PUT** `/api/feeders/{id}/`

Updates all fields of a feeder. All fields are required.

**Request Body:**
```json
{
  "name": "ABC Supermarket (Updated)",
  "address": "123 Main Street, Suite 200",
  ...all other fields
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "ABC Supermarket (Updated)",
  ...updated feeder data
}
```

---

### 5. Partially Update Feeder
**PATCH** `/api/feeders/{id}/`

Updates specific fields of a feeder. Only include fields you want to update.

**Request Body:**
```json
{
  "contact_number": "9999999999",
  "remarks": "Contact number updated"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  ...updated feeder data with new contact_number and remarks
}
```

---

### 6. Delete Feeder
**DELETE** `/api/feeders/{id}/`

Deletes a feeder.

**Response (204 No Content):**
```
(Empty response body)
```

---

### 7. Update Feeder Status
**PATCH** `/api/feeders/{id}/update_status/`

Custom endpoint to update only the status field.

**Request Body:**
```json
{
  "status": "accepted"
}
```

**Valid Status Values:**
- `pending`
- `accepted`
- `key_uploaded`
- `rejected`
- `under_process`

**Response (200 OK):**
```json
{
  "id": 1,
  ...feeder data with updated status
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Invalid status value"
}
```

---

### 8. Get Feeders by Status
**GET** `/api/feeders/by_status/?status={status_value}`

Returns feeders filtered by status.

**Example Request:**
```bash
GET /api/feeders/by_status/?status=pending
```

**Response (200 OK):**
```json
[
  ...array of feeders with pending status
]
```

**Response (400 Bad Request):**
```json
{
  "error": "Status parameter is required"
}
```

---

### 9. Get Feeders by Branch
**GET** `/api/feeders/by_branch/?branch_id={branch_id}`

Returns feeders filtered by branch.

**Example Request:**
```bash
GET /api/feeders/by_branch/?branch_id=1
```

**Response (200 OK):**
```json
[
  ...array of feeders for branch ID 1
]
```

**Response (400 Bad Request):**
```json
{
  "error": "Branch ID parameter is required"
}
```

---

### 10. Get Feeder Statistics
**GET** `/api/feeders/statistics/`

Returns statistics about all feeders.

**Example Request:**
```bash
GET /api/feeders/statistics/
```

**Response (200 OK):**
```json
{
  "total": 150,
  "pending": 45,
  "accepted": 60,
  "rejected": 10,
  "key_uploaded": 25,
  "under_process": 10
}
```

---

### 11. Get Status Choices
**GET** `/api/feeder-status-choices/`

Returns all available status choices for dropdowns.

**Example Request:**
```bash
GET /api/feeder-status-choices/
```

**Response (200 OK):**
```json
[
  {"value": "pending", "label": "Pending"},
  {"value": "accepted", "label": "Accepted"},
  {"value": "key_uploaded", "label": "Key Uploaded"},
  {"value": "rejected", "label": "Rejected"},
  {"value": "under_process", "label": "Under Process"}
]
```

---

### 12. Get Business Nature Choices
**GET** `/api/feeder-business-nature-choices/`

Returns all available business nature choices for dropdowns.

**Example Request:**
```bash
GET /api/feeder-business-nature-choices/
```

**Response (200 OK):**
```json
[
  {"value": "supermarket", "label": "Supermarket"},
  {"value": "textile", "label": "Textile"},
  {"value": "restaurant", "label": "Restaurant"},
  {"value": "Agency/Distribution", "label": "Agency/Distribution"},
  {"value": "retail", "label": "Retail"},
  {"value": "Auto Mobiles", "label": "Auto Mobiles"},
  {"value": "Bakery", "label": "Bakery"},
  {"value": "Boutique", "label": "Boutique"},
  {"value": "Hyper Market", "label": "Hyper Market"},
  {"value": "Lab", "label": "Lab"}
]
```

---

## Error Responses

### 400 Bad Request
Invalid data or missing required fields.

```json
{
  "field_name": ["This field is required."]
}
```

### 404 Not Found
Resource doesn't exist.

```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
Server error.

```json
{
  "detail": "Internal server error"
}
```

---

## Example Usage (Flutter/Dart)

### List Feeders
```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<List<dynamic>> fetchFeeders() async {
  final response = await http.get(
    Uri.parse('http://your-domain.com/api/feeders/'),
  );

  if (response.statusCode == 200) {
    return json.decode(response.body);
  } else {
    throw Exception('Failed to load feeders');
  }
}
```

### Create Feeder
```dart
Future<Map<String, dynamic>> createFeeder(Map<String, dynamic> feederData) async {
  final response = await http.post(
    Uri.parse('http://your-domain.com/api/feeders/'),
    headers: {'Content-Type': 'application/json'},
    body: json.encode(feederData),
  );

  if (response.statusCode == 201) {
    return json.decode(response.body);
  } else {
    throw Exception('Failed to create feeder');
  }
}
```

### Update Status
```dart
Future<void> updateFeederStatus(int feederId, String status) async {
  final response = await http.patch(
    Uri.parse('http://your-domain.com/api/feeders/$feederId/update_status/'),
    headers: {'Content-Type': 'application/json'},
    body: json.encode({'status': status}),
  );

  if (response.statusCode != 200) {
    throw Exception('Failed to update status');
  }
}
```

### Search Feeders
```dart
Future<List<dynamic>> searchFeeders(String query) async {
  final response = await http.get(
    Uri.parse('http://your-domain.com/api/feeders/?search=$query'),
  );

  if (response.statusCode == 200) {
    return json.decode(response.body);
  } else {
    throw Exception('Failed to search feeders');
  }
}
```

---

## Testing the API

### Using Postman
1. Create a new collection called "Feeder API"
2. Add requests for each endpoint
3. Set the base URL to your server
4. Test CRUD operations

### Using cURL

**List all feeders:**
```bash
curl -X GET http://your-domain.com/api/feeders/
```

**Create a feeder:**
```bash
curl -X POST http://your-domain.com/api/feeders/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Shop",
    "address": "Test Address",
    "location": "Test Location",
    "area": "Test Area",
    "district": "Test District",
    "state": "Kerala",
    "contact_person": "Test Person",
    "contact_number": "1234567890",
    "email": "test@test.com",
    "software": "POS",
    "nature": "retail",
    "branch": 1,
    "no_of_system": 2,
    "pincode": "123456",
    "country": "India",
    "installation_date": "2026-03-01",
    "software_amount": "25000.00",
    "module_charges": "5000.00"
  }'
```

**Update status:**
```bash
curl -X PATCH http://your-domain.com/api/feeders/1/update_status/ \
  -H "Content-Type: application/json" \
  -d '{"status": "accepted"}'
```

**Get statistics:**
```bash
curl -X GET http://your-domain.com/api/feeders/statistics/
```

---

## Important Notes

1. **Date Format**: Dates should be in `YYYY-MM-DD` format (e.g., "2026-02-23")
2. **Decimal Fields**: `software_amount` and `module_charges` should be strings with decimal values (e.g., "50000.00")
3. **Module Prices**: `module_prices` is a JSON object/dictionary
4. **Foreign Keys**: `branch` field expects the branch ID (integer)
5. **Arrays**: `modules` and `more_modules` are stored as comma-separated strings but returned as lists in `modules_list` and `more_modules_list` fields

---

## Security Recommendations

For production:
1. Replace `AllowAny` permission with proper authentication (Token, JWT, etc.)
2. Add rate limiting
3. Enable HTTPS
4. Implement proper user permissions
5. Add API versioning (e.g., `/api/v1/feeders/`)

---

## Support

For questions or issues, contact the backend development team.
