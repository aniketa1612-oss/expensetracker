import json
import boto3
from collections import defaultdict
from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("SpendingTrackingTable")
budget_table = dynamodb.Table("budgetTrackingTable")

def lambda_handler(event, context):
    # Scan DynamoDB table to get all records
    response = table.scan()
    items = response.get("Items", [])

    # Get budget data - retrieve the single budget value
    budget_response = budget_table.scan()
    budget_items = budget_response.get("Items", [])
    
    # Extract the budget value (default to 0 if not found)
    current_budget = 0
    if budget_items and len(budget_items) > 0:
        # Assuming the budget is stored in an item with a "budget-id" attribute
        for item in budget_items:
            if "actual-budget" in item:
                try:
                    current_budget = float(item["actual-budget"])
                    break
                except (ValueError, TypeError):
                    # Handle case where budget value isn't a valid number
                    pass
    
    # Organize data for visualization
    spending_data = defaultdict(float)
    item_spending = defaultdict(float)
    monthly_spending = defaultdict(float)
    category_spending = defaultdict(float)  # Added for category tracking
    highest_spent_item = {"item": None, "amount": 0}
    total_spent = 0

    for entry in items:
        date = entry["date"]
        item = entry["item"]
        price = float(entry["price"])
        # Get category if it exists, otherwise use "Other"
        category = entry.get("category", "Other")
        
        # Aggregate total spent per day
        spending_data[date] += price

        # Aggregate total spent per item
        item_spending[item] += price

        # Aggregate total spent per category
        category_spending[category] += price

        # Aggregate total spent per month
        month = date[:7]  # Extract YYYY-MM format
        monthly_spending[month] += price
        
        # Track the item with the highest single expense
        if price > highest_spent_item["amount"]:
            highest_spent_item = {"item": item, "amount": price}
            
        # Track total spent
        total_spent += price

    # Get the top 5 most expensive items
    top_5_items = sorted(item_spending.items(), key=lambda x: x[1], reverse=True)[:5]
    top_5_items = [{"item": item, "amount": amount} for item, amount in top_5_items]

    # Get the highest spending category
    highest_category = max(category_spending.items(), key=lambda x: x[1], default=("None", 0))
    highest_spending_category = {
        "category": highest_category[0],
        "amount": highest_category[1]
    }
    
    # Get category breakdown for visualization
    category_breakdown = [{"category": cat, "amount": amount} for cat, amount in category_spending.items()]
    
    # Calculate projected end-of-month cost
    today = datetime.today()
    current_month = today.strftime("%Y-%m")
    days_passed = today.day
    days_in_month = (datetime(today.year, today.month % 12 + 1, 1) - datetime(today.year, today.month, 1)).days
    total_spent_current_month = monthly_spending.get(current_month, 0)
    projected_cost = (total_spent_current_month / days_passed) * days_in_month if days_passed > 0 else 0
    
    # Calculate budget status
    budget_remaining = current_budget - total_spent_current_month
    budget_percentage = (total_spent_current_month / current_budget) * 100 if current_budget > 0 else 0
    
    # Determine spending trend by comparing recent days
    # This would require more sophisticated analysis with time-series data
    # For now, we'll return a simple placeholder
    spending_trend = "steady"  # Options could be: "increasing", "decreasing", "steady"
    
    # Calculate spending velocity (average daily spend this month)
    daily_spending_rate = total_spent_current_month / days_passed if days_passed > 0 else 0

    return {
        "statusCode": 200,
        "headers": {
            #"Access-Control-Allow-Origin": "*",  # Enable CORS
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "spending_data": dict(spending_data),  # Convert defaultdict to regular dict for JSON serialization
            "highest_spent_item": highest_spent_item,
            "top_5_items": top_5_items,
            "monthly_spending": dict(monthly_spending),
            "projected_cost": projected_cost,
            "current_budget": current_budget,
            "budget_remaining": budget_remaining,
            "budget_percentage": budget_percentage,
            "highest_spending_category": highest_spending_category,
            "category_breakdown": category_breakdown,
            "spending_trend": spending_trend,
            "daily_spending_rate": daily_spending_rate,
            "total_spent": total_spent
        })

    }
