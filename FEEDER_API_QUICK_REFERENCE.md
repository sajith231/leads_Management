# Feeder API - Quick Reference Guide

## 📱 Mobile App API Endpoints

### Base URL
```
http://your-domain.com/api/
```

---

## 🚀 Most Used Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/feeders/` | Get all feeders (with filters) |
| `POST` | `/api/feeders/` | Create new feeder |
| `GET` | `/api/feeders/{id}/` | Get specific feeder |
| `PATCH` | `/api/feeders/{id}/` | Update feeder (partial) |
| `DELETE` | `/api/feeders/{id}/` | Delete feeder |
| `PATCH` | `/api/feeders/{id}/update_status/` | Update status only |
| `GET` | `/api/feeders/statistics/` | Get statistics |

---

## 🔍 Query Parameters (Filters)

Add to `/api/feeders/` endpoint:

```
?status=pending              # Filter by status
?branch_id=1                 # Filter by branch
?district=Malappuram        # Filter by district
?search=supermarket         # Search in name, software, contact person
```

**Combine filters:**
```
/api/feeders/?status=pending&branch_id=1&search=super
```

---

## 📊 Quick Examples

### 1. Get All Feeders
```bash
GET /api/feeders/
```

### 2. Get Pending Feeders
```bash
GET /api/feeders/?status=pending
```

### 3. Create New Feeder
```bash
POST /api/feeders/
Content-Type: application/json

{
  "name": "Shop Name",
  "address": "Address",
  "location": "Location",
  "area": "Area",
  "district": "District",
  "state": "State",
  "contact_person": "Person Name",
  "contact_number": "1234567890",
  "email": "email@example.com",
  "software": "POS",
  "nature": "retail",
  "branch": 1,
  "no_of_system": 2,
  "pincode": "123456",
  "country": "India",
  "installation_date": "2026-03-01",
  "software_amount": "50000.00",
  "module_charges": "10000.00"
}
```

### 4. Update Status
```bash
PATCH /api/feeders/1/update_status/
Content-Type: application/json

{
  "status": "accepted"
}
```

### 5. Get Statistics
```bash
GET /api/feeders/statistics/

Response:
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

## 📋 Status Values

| Value | Label |
|-------|-------|
| `pending` | Pending |
| `accepted` | Accepted |
| `key_uploaded` | Key Uploaded |
| `rejected` | Rejected |
| `under_process` | Under Process |

---

## 🏪 Business Nature Values

- `supermarket` - Supermarket
- `textile` - Textile
- `restaurant` - Restaurant
- `Agency/Distribution` - Agency/Distribution
- `retail` - Retail
- `Auto Mobiles` - Auto Mobiles
- `Bakery` - Bakery
- `Boutique` - Boutique
- `Hyper Market` - Hyper Market
- `Lab` - Lab

---

## 📱 Flutter Code Snippets

### Fetch Feeders
```dart
Future<List<dynamic>> fetchFeeders() async {
  final response = await http.get(
    Uri.parse('http://your-domain.com/api/feeders/'),
  );
  if (response.statusCode == 200) {
    return json.decode(response.body);
  }
  throw Exception('Failed to load feeders');
}
```

### Create Feeder
```dart
final feeder = {
  'name': 'Shop Name',
  'address': 'Address',
  // ... other fields
};

final response = await http.post(
  Uri.parse('http://your-domain.com/api/feeders/'),
  headers: {'Content-Type': 'application/json'},
  body: json.encode(feeder),
);
```

### Update Status
```dart
final response = await http.patch(
  Uri.parse('http://your-domain.com/api/feeders/$id/update_status/'),
  headers: {'Content-Type': 'application/json'},
  body: json.encode({'status': 'accepted'}),
);
```

---

## ✅ What Was Implemented

### Files Modified:
1. ✅ [app2/serializers.py](app2/serializers.py) - Enhanced FeederSerializer
2. ✅ [app2/views.py](app2/views.py) - Added API ViewSet and functions
3. ✅ [app2/urls.py](app2/urls.py) - Added API routes

### Files Created:
1. ✅ [FEEDER_API_DOCUMENTATION.md](FEEDER_API_DOCUMENTATION.md) - Complete API docs
2. ✅ [FEEDER_API_QUICK_REFERENCE.md](FEEDER_API_QUICK_REFERENCE.md) - This file

---

## 🔒 Important Notes

1. **No Existing Functionality Changed** - All web views remain intact
2. **API is Separate** - Uses `/api/` prefix to avoid conflicts
3. **Ready for Mobile** - All CRUD operations available
4. **Filtering Supported** - Multiple query parameters
5. **Detailed Responses** - Includes readable labels and formatted data

---

## 🧪 Test the API

Run your Django server:
```bash
python manage.py runserver
```

Visit in browser:
```
http://127.0.0.1:8000/api/feeders/
```

You should see Django REST Framework's browsable API interface!

---

For detailed documentation, see [FEEDER_API_DOCUMENTATION.md](FEEDER_API_DOCUMENTATION.md)
