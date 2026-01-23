# Quick Reference: Items Display Feature

## What's New?

When you submit a lead with multiple items, they are now properly displayed throughout the application:

### 1. **In the Directory (Left Panel)**
```
┌─────────────────────────────────┐
│ Lead: John Doe                  │
│ Phone: 9876543210              │
│ Status: Active                  │
│ Priority: 🔴 High              │
│ 📦 3 items  ← NEW!              │  ← Green badge shows item count
│ Campaign: Q1 2024               │
└─────────────────────────────────┘
```

**Hover over the badge to see item preview:**
```
┌──────────────────────┐
│ Item 1 (Qty: 5)      │
│ Item 2 (Qty: 10)     │
│ Item 3 (Qty: 2)      │
└──────────────────────┘
```

### 2. **In the Form (Right Panel)**
When you click a lead in the directory, the form loads with a complete items table:

```
┌────────────────────────────────────────────────────────────────┐
│ REQUIREMENTS SECTION                                            │
├─────┬──────────┬──────────────┬──────┬───────┬─────┬──────┬────┤
│  #  │ Section  │ Item Name    │ Unit │ Price │ Qty │ Total│ ❌ │
├─────┼──────────┼──────────────┼──────┼───────┼─────┼──────┼────┤
│ 1   │ GENERAL  │ Item A       │ pcs  │ 100   │ 5   │ 500  │    │
│ 2   │ HARDWARE │ Item B       │ kg   │ 50    │ 10  │ 500  │    │
│ 3   │ SOFTWARE │ Item C       │ pcs  │ 25    │ 2   │ 50   │    │
├─────┴──────────┴──────────────┴──────┴───────┴─────┴──────┴────┤
│ Grand Total:                                            1050   │
└────────────────────────────────────────────────────────────────┘
```

## How It Works

### User Journey:

**Step 1: Submit Lead with Items**
```
New Lead Form
│
├─ Fill in customer details
│
├─ Add items to requirements table
│  ├─ Item 1: Qty 5
│  ├─ Item 2: Qty 10
│  └─ Item 3: Qty 2
│
└─ Click "Submit Form"
    └─ Lead created & items saved to database
```

**Step 2: View Items in Directory**
```
Active Leads Directory
│
├─ Lead appears in list
│
└─ Shows "📦 3 items" badge
   └─ Hover to see quick preview
```

**Step 3: Click Lead to View Details**
```
Directory List                Form Section
│                           │
├─ Click on "John Doe"  ────→ └─ Form loads
│                           ├─ Items table populates
│                           ├─ Shows all 3 items
│                           └─ Ready to edit
```

**Step 4: Edit or Add More**
```
Items Table
│
├─ Edit existing items (change qty/price)
├─ Remove items with ❌ button
├─ Add new items with "+ Add Item"
│
└─ Save changes with "Edit Lead" button
```

## Key Features

### ✅ Item Count Badge
- **Location**: In each lead item in the directory
- **Color**: 
  - 🟢 Green = Has items (with count)
  - ⚫ Gray = No items
- **Interactive**: Hover to see items, click lead to load details

### ✅ Items Table
- **Columns**: Section | Item Name | Unit | Price | Qty | Total | Remove
- **Auto-calculation**: Total = Price × Quantity
- **Grand Total**: Automatically calculated at bottom
- **Editable**: Change quantities and prices
- **Removable**: Delete items with trash button
- **Addable**: Add new items with "+ Add Item" button

### ✅ Notifications
- When you load a lead: `✅ Loaded: John Doe (Business) | 📦 3 items loaded`
- When you add an item: Shows in toast notification
- When you remove an item: Confirms removal

### ✅ Data Persistence
- All items saved to database when you submit/edit
- Items remain associated with the lead
- Can be viewed/edited anytime by clicking the lead

## Database Structure

```
Lead (Main Record)
├─ id: 1
├─ ownerName: "John Doe"
├─ phoneNo: "9876543210"
├─ status: "Active"
│
└─ RequirementItem (Related Items)
   ├─ Item 1
   │  ├─ item_name: "Item A"
   │  ├─ quantity: 5
   │  ├─ price: 100.00
   │  └─ total: 500.00
   │
   ├─ Item 2
   │  ├─ item_name: "Item B"
   │  ├─ quantity: 10
   │  ├─ price: 50.00
   │  └─ total: 500.00
   │
   └─ Item 3
      ├─ item_name: "Item C"
      ├─ quantity: 2
      ├─ price: 25.00
      └─ total: 50.00
```

## Troubleshooting

### Issue: Items don't show in directory badge

**Solution:**
1. Make sure items were added before submitting the form
2. Check that the form submission completed successfully
3. Refresh the page to reload from database

### Issue: Items table empty when I click a lead

**Solution:**
1. The lead might not have any items - check the badge
2. Try refreshing the page
3. Check browser console (F12) for error messages

### Issue: Grand total not calculating

**Solution:**
1. Make sure price and quantity are filled for each item
2. Price must be a number (no letters or symbols)
3. Try refreshing the page

### Issue: Can't edit item quantities

**Solution:**
1. Items table fields might be read-only
2. Click "Edit Lead" button to enable editing mode
3. After editing, click "Edit Lead" button again to save

## Console Logging

For developers, the console shows detailed logs:

```javascript
// When loading a lead:
📝 Lead clicked: John Doe
📦 Requirements JSON: Available
📊 Item count: 3

// When populating items:
📦 Populating requirements for lead: John Doe
✅ Parsed requirements from JSON: Array(3)
Found requirements: 3
📋 Loading 3 requirements
[1] Requirement: {item_name: "Item A", quantity: 5, ...}
[2] Requirement: {item_name: "Item B", quantity: 10, ...}
[3] Requirement: {item_name: "Item C", quantity: 2, ...}
✅ Requirements loaded successfully

// Notifications:
✅ Loaded 3 items
```

Open browser DevTools (F12 → Console) to see these logs.

## API/Backend Data Format

### Requirements JSON Structure:
```json
[
  {
    "id": 1,
    "item_id": 10,
    "item_name": "Item A",
    "section": "GENERAL",
    "unit": "pcs",
    "price": 100.0,
    "quantity": 5
  },
  {
    "id": 2,
    "item_id": 11,
    "item_name": "Item B",
    "section": "HARDWARE",
    "unit": "kg",
    "price": 50.0,
    "quantity": 10
  },
  {
    "id": 3,
    "item_id": 12,
    "item_name": "Item C",
    "section": "SOFTWARE",
    "unit": "pcs",
    "price": 25.0,
    "quantity": 2
  }
]
```

This JSON is stored in the `data-requirements` attribute and parsed by JavaScript.

## Important Notes

⚠️ **Items are linked to leads**: Each item belongs to exactly one lead
⚠️ **Items persist**: Once saved, items stay with the lead (unless deleted)
⚠️ **Quantities matter**: Changing quantity automatically updates the total
⚠️ **Prices are editable**: Can override item master price in the form
⚠️ **Grand total includes all items**: Sum of all item totals

## For Support

If you have questions:
1. Check the IMPLEMENTATION_SUMMARY.md file for technical details
2. Review the flow diagrams in this document
3. Check browser console for error messages
4. Verify the database has RequirementItem records

## Quick Commands (For Developers)

### View all items for a lead (Django shell):
```python
from app5.models import Lead, RequirementItem

lead = Lead.objects.get(id=1)
items = lead.requirements.all()

for item in items:
    print(f"{item.item_name}: Qty={item.quantity}, Price={item.price}, Total={item.total}")
```

### Check requirements JSON:
```python
lead = Lead.objects.get(id=1)
print(lead.requirements_json)
```

### Count items for a lead:
```python
lead = Lead.objects.get(id=1)
print(lead.requirements.count())  # Returns: 3
```
