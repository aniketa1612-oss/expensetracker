import json
import boto3
from collections import defaultdict
from datetime import datetime
from decimal import Decimal # Use Decimal for currency
import calendar # Better for days in month

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("SpendingTrackingTable")
budget_table = dynamodb.Table("budgetTrackingTable")

def lambda_handler(event, context):
    # Scan DynamoDB table to get all records, handling pagination
    response = table.scan()
    items = response.get("Items", [])
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get("Items", []))

    # Get budget data efficiently using get_item
    try:
        # Assuming your budget item has a primary key like {'budget-id': 'current'}
        budget_response = budget_table.get_item(Key={'budget-id': 'current'})
        current_budget = budget_response.get('Item', {}).get('actual-budget', Decimal('0'))
        current_budget = float(current_budget) # Convert to float for JSON if needed, but Decimal is safer
    except Exception as e:
        current_budget = 0

    # Organize data for visualization
    spending_data = defaultdict(float)
    item_spending = defaultdict(float)
    monthly_spending = defaultdict(float)
    category_spending = defaultdict(float)
    highest_spent_item = {"item": None, "amount": 0}
    total_spent = 0

    for entry in items:
        # Use Decimal for precision with money
        price = float(entry.get("price", 0))
        date = entry.get("date", "")
        item = entry.get("item", "Unknown Item")
        category = entry.get("category", "Other")

        spending_data[date] += price
        item_spending[item] += price
        category_spending[category] += price
        month = date[:7]
        monthly_spending[month] += price
        
        if price > highest_spent_item["amount"]:
            highest_spent_item = {"item": item, "amount": price}
            
        total_spent += price

    top_5_items = [{"item": item, "amount": amount} for item, amount in sorted(item_spending.items(), key=lambda x: x[1], reverse=True)[:5]]
    
    highest_category = max(category_spending.items(), key=lambda x: x[1], default=("None", 0))
    highest_spending_category = {"category": highest_category[0], "amount": highest_category[1]}
    
    category_breakdown = [{"category": cat, "amount": amount} for cat, amount in category_spending.items()]
    
    # Calculate projected cost
    today = datetime.today()
    current_month_str = today.strftime("%Y-%m")
    days_passed = today.day
    # A more robust way to get days in month
    _, days_in_month = calendar.monthrange(today.year, today.month)
    
    total_spent_current_month = monthly_spending.get(current_month_str, 0)
    projected_cost = (total_spent_current_month / days_passed) * days_in_month if days_passed > 0 else 0
    
    # Budget calculations
    budget_remaining = current_budget - total_spent_current_month
    budget_percentage = (total_spent_current_month / current_budget) * 100 if current_budget > 0 else 0
    daily_spending_rate = total_spent_current_month / days_passed if days_passed > 0 else 0

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",  # CRITICAL: This must be enabled
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "spending_data": dict(spending_data),
            "highest_spent_item": highest_spent_item,
            "top_5_items": top_5_items,
            "monthly_spending": dict(monthly_spending),
            "projected_cost": projected_cost,
            "current_budget": current_budget,
            "budget_remaining": budget_remaining,
            "budget_percentage": budget_percentage,
            "highest_spending_category": highest_spending_category,
            "category_breakdown": category_breakdown,
            "spending_trend": "steady", # Placeholder
            "daily_spending_rate": daily_spending_rate,
            "total_spent": total_spent
        })
    }
