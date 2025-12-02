#!/usr/bin/env python3
"""
Full Org Return Dashboard Generator
Shows comprehensive YTD and per-month metrics including:
- KW closed
- Number of closed deals
- Sit rate and close rate
- Daily averages
- Revenue ($5.5/watt) and Profit ($0.67/watt)
"""

import requests
from datetime import datetime, timedelta
from collections import defaultdict
import json
import time

# State name to abbreviation mapping
STATE_MAP = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY'
}

# Podio credentials
CLIENT_ID = 'gpt-operator'
CLIENT_SECRET = 'yn58tFMJO0HR8JRnUgKOWKph5FEq1Fn3WgWA4NA7oS4pMSSHmAuXTpxcE6hHtwPB'

# Full Org Internal App (contains Full Org assigned appointments only)
FULL_ORG_APP_ID = '30430059'
FULL_ORG_APP_TOKEN = 'daf910d595cc805cf91a4ab4edc293cb'

# Financial constants
REVENUE_PER_WATT = 5.5
PROFIT_PER_WATT = 0.57  # Net profit per watt

# Alternative profit calculation
PROFIT_PER_CLOSED_DEAL = 3212  # Net profit per closed deal

# Cost scenarios for analysis
COST_AT_COST = 350  # At cost to generate revenue
COST_PREMIUM = 550  # Premium cost

print("=" * 80)
print("FULL ORG RETURN DASHBOARD GENERATOR")
print("=" * 80)

def retry_api_call(func, max_retries=5, initial_delay=2):
    """Retry API calls on failure with exponential backoff"""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return func()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            if attempt < max_retries - 1:
                print(f"      ⚠️  Connection error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                print(f"      ⏳ Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"      ❌ All {max_retries} retry attempts failed")
                raise
    return None

def get_access_token():
    """Get Podio access token"""
    print("\n🔑 Authenticating with Podio...")
    data = {
        'grant_type': 'app',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'app_id': FULL_ORG_APP_ID,
        'app_token': FULL_ORG_APP_TOKEN
    }

    response = retry_api_call(lambda: requests.post('https://podio.com/oauth/token', data=data))

    if response.status_code != 200:
        print(f"❌ Auth failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return None

    token = response.json()['access_token']
    print("✅ Authentication successful")
    return token

def fetch_all_items(access_token):
    """Fetch all items from Full Org Internal App"""
    print("\n📋 Fetching all appointment data from Full Org Internal...")

    all_items = []

    headers = {
        'Authorization': f'OAuth2 {access_token}',
        'Content-Type': 'application/json'
    }

    # Fetch current month first, then fetch rest by year
    today = datetime.now().date()
    current_month_start = today.replace(day=1).strftime('%Y-%m-%d')
    current_month_end = today.strftime('%Y-%m-%d')

    print(f"\n   🎯 Fetching CURRENT MONTH first ({current_month_start} to {current_month_end})...")

    offset = 0
    limit = 500
    current_month_items = 0

    while True:
        body = {
            'limit': limit,
            'offset': offset,
            'sort_by': 'appointment-date',
            'sort_desc': False,
            'filters': {
                'appointment-date': {
                    'from': current_month_start,
                    'to': current_month_end
                }
            }
        }

        try:
            response = retry_api_call(
                lambda: requests.post(
                    f"https://api.podio.com/item/app/{FULL_ORG_APP_ID}/filter/",
                    headers=headers,
                    json=body,
                    timeout=90
                )
            )

            if response.status_code != 200:
                print(f"      ⚠️  Got status {response.status_code}, stopping current month fetch")
                break

            items = response.json().get('items', [])
            if not items:
                break

            all_items.extend(items)
            current_month_items += len(items)
            print(f"      Current month: {current_month_items} appointments...")

            if len(items) < limit:
                break

            offset += limit

        except Exception as e:
            print(f"      ⚠️  Error fetching current month: {e}")
            break

    print(f"   ✅ Fetched {current_month_items} appointments from current month")

    # Then fetch rest of 2025 and 2024
    years_to_fetch = ['2025', '2024', '2023']

    for year in years_to_fetch:
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'
        print(f"\n   Fetching {year} data...")

        offset = 0
        limit = 500
        year_items = 0

        while True:
            body = {
                'limit': limit,
                'offset': offset,
                'sort_by': 'appointment-date',
                'sort_desc': False,
                'filters': {
                    'appointment-date': {
                        'from': start_date,
                        'to': end_date
                    }
                }
            }

            # Use retry logic for API calls
            try:
                response = retry_api_call(
                    lambda: requests.post(
                        f"https://api.podio.com/item/app/{FULL_ORG_APP_ID}/filter/",
                        headers=headers,
                        json=body,
                        timeout=90
                    )
                )

                if response.status_code != 200:
                    print(f"      ⚠️  Got status {response.status_code}, stopping {year} fetch")
                    break

                items = response.json().get('items', [])

                if not items:
                    break

                all_items.extend(items)
                year_items += len(items)
                print(f"      {year}: {year_items} appointments...")

                if len(items) < limit:
                    break

                offset += limit

            except Exception as e:
                print(f"      ❌ Error fetching {year}: {e}")
                break

        print(f"   ✅ Fetched {year_items} appointments from {year}")

    print(f"\n✅ Total appointments fetched: {len(all_items)}")

    # Deduplicate by item_id (in case current month was fetched twice)
    seen_ids = set()
    unique_items = []
    for item in all_items:
        item_id = item.get('item_id')
        if item_id and item_id not in seen_ids:
            seen_ids.add(item_id)
            unique_items.append(item)

    if len(unique_items) < len(all_items):
        print(f"   ℹ️  Removed {len(all_items) - len(unique_items)} duplicates")
        print(f"   ✅ Unique appointments: {len(unique_items)}")

    return unique_items

def get_field_value(item, external_id):
    """Extract field value from Podio item by external_id"""
    for field in item.get('fields', []):
        if field.get('external_id') == external_id:
            values = field.get('values', [])
            if not values:
                return None

            field_type = field.get('type')

            if field_type == 'category':
                val = values[0].get('value', {})
                return val.get('text', '') if isinstance(val, dict) else str(val)
            elif field_type == 'number':
                return values[0].get('value', 0)
            elif field_type == 'date':
                return values[0].get('start', '')
            elif field_type == 'contact':
                val = values[0].get('value', {})
                return val.get('name', '') if isinstance(val, dict) else ''
            elif field_type == 'text':
                return values[0].get('value', '')
            else:
                return str(values[0].get('value', ''))

    return None

def parse_date(date_str):
    """Parse date string to date object"""
    if not date_str:
        return None
    try:
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        else:
            return datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
    except:
        return None

def process_appointments(items):
    """Process all appointments and organize by date - ONLY ASSIGNED APPOINTMENTS"""
    print("\n🔍 Processing appointment data (filtering for assigned appointments only)...")

    appointments_by_date = defaultdict(list)
    total_processed = 0
    assigned_count = 0

    # Track date ranges to debug MTD issue
    earliest_date = None
    latest_date = None

    for item in items:
        total_processed += 1

        # CRITICAL: Only count appointments that have someone assigned (closer OR partner)
        closer_assigned = get_field_value(item, 'closer-assigned')
        partner_assigned = get_field_value(item, 'partner-assigned') or ''

        # Skip if NEITHER closer nor partner is assigned
        if (not closer_assigned or closer_assigned == '') and (not partner_assigned or partner_assigned == ''):
            continue  # Skip completely unassigned appointments

        # EXCLUDE CHASE & INFINITE AI APPOINTMENTS - Only include Team Captain appointments
        # Check if closer is Chase or if partner/agent indicates Chase
        agent = get_field_value(item, 'agent') or ''
        set_by = get_field_value(item, 'set-by-3') or ''

        # Skip if Chase is mentioned in closer, partner, or agent fields
        if 'chase' in str(closer_assigned).lower() or \
           'chase' in str(partner_assigned).lower() or \
           'chase' in str(agent).lower():
            continue  # Skip Chase appointments

        # EXCLUDE INFINITE AI APPOINTMENTS
        if 'infinite' in str(set_by).lower() or \
           'infinite ai' in str(agent).lower() or \
           'infinite' in str(partner_assigned).lower():
            continue  # Skip Infinite AI appointments

        assigned_count += 1

        # Get appointment date
        appt_date_str = get_field_value(item, 'appointment-date')
        appt_date = parse_date(appt_date_str)

        if not appt_date:
            continue

        # Get sit status
        sit_status = get_field_value(item, 'sit')
        closer_reset_status = get_field_value(item, 'closer-reset-status')

        # Count as sit if:
        # 1. Sit field = "Yes" or contains "Reset by Closer"
        # 2. Closer Reset Status field contains "Sit Yes"
        is_sit = (sit_status and (sit_status.lower() == 'yes' or 'reset by closer' in sit_status.lower())) or \
                 (closer_reset_status and 'sit yes' in closer_reset_status.lower())

        # Get close status
        close_status = get_field_value(item, 'status') or ''
        is_closed = 'closed' in close_status.lower() and '$' in close_status

        # Get KW (only for closed deals)
        kw = 0
        if is_closed:
            kw_val = get_field_value(item, 'kw-size') or get_field_value(item, 'kw')
            try:
                kw = float(kw_val) if kw_val else 0
            except:
                kw = 0

        # Get customer name (for tracking)
        customer = get_field_value(item, 'customer-name') or get_field_value(item, 'customer') or ''

        # Extract state from address
        state = None
        address_val = get_field_value(item, 'address')
        if address_val:
            if isinstance(address_val, dict):
                state = address_val.get('state', '')
            elif isinstance(address_val, str):
                # Address format: "Street, ZIP City, STATE" or "Street, City, State, COUNTRY"
                try:
                    parts = address_val.split(',')
                    # Check the last few parts for state
                    for part in reversed(parts[-3:]):
                        part_clean = part.strip().lower()

                        # Skip common country names
                        if part_clean in ['usa', 'united states', 'us']:
                            continue

                        # Check if it's a 2-letter state code
                        if len(part_clean) == 2 and part_clean.isalpha():
                            state = part_clean.upper()
                            break

                        # Check if it's a full state name
                        if part_clean in STATE_MAP:
                            state = STATE_MAP[part_clean]
                            break
                except:
                    pass

        appt_data = {
            'date': appt_date,
            'is_sit': is_sit,
            'is_closed': is_closed,
            'kw': kw,
            'customer': customer,
            'closer': closer_assigned,
            'state': state if state else 'Unknown',
            'sit_status': sit_status  # Store original sit status to check if updated
        }

        appointments_by_date[appt_date].append(appt_data)

        # Track date range
        if earliest_date is None or appt_date < earliest_date:
            earliest_date = appt_date
        if latest_date is None or appt_date > latest_date:
            latest_date = appt_date

    valid_appts = sum(len(v) for v in appointments_by_date.values())
    print(f"✅ Processed {total_processed} total records")
    print(f"✅ Filtered to {assigned_count} ASSIGNED appointments (Full Org)")
    print(f"✅ Valid appointments with dates: {valid_appts}")
    print(f"📅 Date range in data: {earliest_date} to {latest_date}")
    return appointments_by_date

def find_ytd_start(appointments_by_date):
    """Find the first date with 3+ appointments OR the first appointment date"""
    print("\n📅 Finding YTD start date...")

    if not appointments_by_date:
        return datetime.now().date()

    # Sort dates
    sorted_dates = sorted(appointments_by_date.keys())

    # Find first date with 3+ appointments
    for date in sorted_dates:
        if len(appointments_by_date[date]) >= 3:
            print(f"✅ YTD start: {date} (first day with 3+ appointments)")
            return date

    # If no date with 3+ appointments, use the first appointment date
    first_date = sorted_dates[0]
    print(f"✅ YTD start: {first_date} (first appointment in system)")
    return first_date

def calculate_metrics(appointments):
    """Calculate metrics for a list of appointments"""
    total_appts = len(appointments)

    # DISPOSITION RULE:
    # - Total Appts = ALL assigned appointments
    # - Dispositioned = appointments with sit_status set (Yes, No, or any value)
    # - Sit Rate = Sits / Dispositioned (NOT Sits / Total)
    # This is because undispositioned appointments haven't been worked yet

    # Count dispositioned appointments (those with ANY sit status set)
    dispositioned = sum(1 for a in appointments if a.get('sit_status'))
    sits = sum(1 for a in appointments if a['is_sit'])
    closed = sum(1 for a in appointments if a['is_closed'])
    total_kw = sum(a['kw'] for a in appointments)

    # Sit rate uses DISPOSITIONED count, not total
    sit_rate = (sits / dispositioned * 100) if dispositioned > 0 else 0
    close_rate = (closed / sits * 100) if sits > 0 else 0

    # Revenue (KW × 1000 to convert to watts)
    revenue = total_kw * 1000 * REVENUE_PER_WATT

    # Count states (use all appts, not filtered)
    state_counts = {}
    for a in appointments:
        state = a.get('state', 'Unknown')
        state_counts[state] = state_counts.get(state, 0) + 1

    # Format states as "STATE (count)" sorted by count
    states_list = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)
    states_formatted = [f"{state} ({count})" for state, count in states_list]

    return {
        'total_appts': total_appts,
        'dispositioned': dispositioned,
        'sits': sits,
        'closed': closed,
        'kw': round(total_kw, 2),
        'sit_rate': round(sit_rate, 1),
        'close_rate': round(close_rate, 1),
        'revenue': round(revenue, 2),
        'states': states_formatted
    }

def calculate_monthly_stats(appointments_by_date, ytd_start):
    """Calculate per-month statistics"""
    print("\n📊 Calculating monthly statistics...")

    monthly_data = defaultdict(list)

    for date, appts in appointments_by_date.items():
        if date >= ytd_start:
            month_key = date.strftime('%Y-%m')
            monthly_data[month_key].extend(appts)

    monthly_stats = {}
    for month_key in sorted(monthly_data.keys()):
        appts = monthly_data[month_key]
        monthly_stats[month_key] = calculate_metrics(appts)

    print(f"✅ Calculated stats for {len(monthly_stats)} months")
    return monthly_stats

def calculate_daily_averages(appointments_by_date, ytd_start):
    """Calculate daily averages since YTD start"""
    print("\n📈 Calculating daily averages...")

    # Filter appointments from YTD start
    ytd_appts = []
    for date, appts in appointments_by_date.items():
        if date >= ytd_start:
            ytd_appts.extend(appts)

    # Calculate number of days
    today = datetime.now().date()
    days_elapsed = (today - ytd_start).days + 1  # +1 to include start day

    if days_elapsed <= 0:
        return {'daily_appts': 0, 'daily_closed': 0, 'daily_sits': 0}

    total_appts = len(ytd_appts)
    total_sits = sum(1 for a in ytd_appts if a['is_sit'])
    total_closed = sum(1 for a in ytd_appts if a['is_closed'])

    daily_avgs = {
        'daily_appts': round(total_appts / days_elapsed, 2),
        'daily_closed': round(total_closed / days_elapsed, 2),
        'daily_sits': round(total_sits / days_elapsed, 2)
    }

    print(f"✅ Daily averages calculated over {days_elapsed} days")
    return daily_avgs

def calculate_daily_averages_active_days(appointments_by_date, start_date, end_date=None):
    """Calculate daily averages based on ACTIVE days only (days with appointments)"""
    if end_date is None:
        end_date = datetime.now().date()

    # Filter appointments in date range
    filtered_appts = []
    active_days = set()

    for date, appts in appointments_by_date.items():
        if start_date <= date <= end_date:
            filtered_appts.extend(appts)
            active_days.add(date)

    # Count only days that had appointments
    num_active_days = len(active_days)

    if num_active_days == 0:
        return {
            'daily_appts': 0,
            'daily_sits': 0,
            'daily_closed': 0,
            'active_days': 0
        }

    total_appts = len(filtered_appts)
    total_sits = sum(1 for a in filtered_appts if a['is_sit'])
    total_closed = sum(1 for a in filtered_appts if a['is_closed'])

    return {
        'daily_appts': round(total_appts / num_active_days, 2),
        'daily_sits': round(total_sits / num_active_days, 2),
        'daily_closed': round(total_closed / num_active_days, 2),
        'active_days': num_active_days
    }

def generate_html(ytd_stats, since_start_stats, mtd_stats, wtd_stats, monthly_stats, daily_avgs, since_start_date, week_start, ytd_daily_avgs, mtd_daily_avgs, wtd_daily_avgs):
    """Generate HTML dashboard"""
    print("\n📝 Generating HTML dashboard...")

    today = datetime.now().date()
    month_start = today.replace(day=1)
    ytd_2025_start = datetime(2025, 1, 1).date()

    # Generate monthly breakdown HTML
    monthly_rows = ""

    for month_key in sorted(monthly_stats.keys(), reverse=True):
        stats = monthly_stats[month_key]
        month_name = datetime.strptime(month_key, '%Y-%m').strftime('%B %Y')

        monthly_rows += f"""
        <tr>
            <td>{month_name}</td>
            <td>{stats['total_appts']}</td>
            <td>{stats['sits']}</td>
            <td>{stats['sit_rate']}%</td>
            <td>{stats['closed']}</td>
            <td>{stats['close_rate']}%</td>
            <td>{stats['kw']}</td>
            <td>${stats['revenue']:,.0f}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Org Return - Complete Performance Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e22ce 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
            font-size: 13px;
        }}

        .container {{
            max-width: 1800px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 25px;
        }}

        .header h1 {{
            font-size: 2.2em;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 0 30px rgba(251, 191, 36, 0.5);
        }}

        .header p {{
            font-size: 1em;
            opacity: 0.9;
        }}

        .last-updated {{
            text-align: center;
            opacity: 0.7;
            margin-bottom: 20px;
            font-size: 0.85em;
        }}

        /* Summary Cards */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 25px;
            margin-bottom: 40px;
        }}

        .summary-card {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 18px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .summary-card h2 {{
            font-size: 1.3em;
            margin-bottom: 12px;
            border-bottom: 2px solid rgba(251, 191, 36, 0.5);
            padding-bottom: 8px;
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}

        .metric {{
            background: rgba(255, 255, 255, 0.05);
            padding: 10px;
            border-radius: 8px;
        }}

        .metric-label {{
            font-size: 0.8em;
            opacity: 0.8;
            margin-bottom: 5px;
        }}

        .metric-value {{
            font-size: 1.4em;
            font-weight: bold;
            color: #fbbf24;
        }}

        .metric-value.success {{
            color: #4ade80;
        }}

        .metric-value.info {{
            color: #60a5fa;
        }}

        /* Daily Averages Section */
        .daily-avg-section {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .daily-avg-section h2 {{
            font-size: 1.5em;
            margin-bottom: 15px;
            text-align: center;
            color: #fbbf24;
        }}

        .daily-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}

        .daily-box {{
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}

        .daily-box .label {{
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 8px;
        }}

        .daily-box .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #4ade80;
        }}

        /* Monthly Breakdown Table */
        .monthly-section {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 18px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            margin-bottom: 20px;
        }}

        .monthly-section h2 {{
            font-size: 1.5em;
            margin-bottom: 15px;
            text-align: center;
            color: #fbbf24;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            overflow: hidden;
            font-size: 0.95em;
        }}

        th {{
            background: rgba(251, 191, 36, 0.2);
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid rgba(251, 191, 36, 0.5);
        }}

        td {{
            padding: 8px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        tr:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}

        .footer {{
            text-align: center;
            margin-top: 40px;
            opacity: 0.6;
            font-size: 0.95em;
        }}

        .footer p {{
            margin: 5px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 FULL ORG RETURN</h1>
            <p>Comprehensive Performance Dashboard - Real Podio Data</p>
        </div>

        <div class="last-updated">
            Last Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
            <span style="font-size: 0.75em; opacity: 0.7; font-style: italic;">cron job: hourly from 8am to 8pm daily | last ran: {datetime.now().strftime('%B %d, %Y at %I:%M %p').lower()}</span>
        </div>

        <!-- Fixed floating refresh timer -->
        <div id="refreshTimer" style="position: fixed; bottom: 20px; right: 20px; background: rgba(0, 0, 0, 0.9); color: white; padding: 15px 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); z-index: 9999; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; min-width: 200px;">
            <div id="nextRefresh" style="font-size: 13px; font-weight: 600; margin-bottom: 5px; color: #fff;"></div>
            <div id="countdown" style="font-size: 14px; font-weight: 700; color: #00ff88;"></div>
        </div>

        <!-- Summary Cards: YTD 2025, MTD, WTD -->
        <div class="summary-grid">
            <!-- YTD 2025 Card -->
            <div class="summary-card">
                <h2>📆 YTD 2025 (Year to Date)</h2>
                <p style="opacity: 0.7; margin-bottom: 15px; font-size: 0.9em;">Jan 1, 2025 to {today}</p>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-label">Total Appointments</div>
                        <div class="metric-value info">{ytd_stats['total_appts']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Dispositioned</div>
                        <div class="metric-value" style="color: #ffa500;">{ytd_stats['dispositioned']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Sits</div>
                        <div class="metric-value info">{ytd_stats['sits']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Sit Rate</div>
                        <div class="metric-value success">{ytd_stats['sit_rate']}%</div>
                        <div style="font-size: 0.7em; opacity: 0.7;">(Sits/Dispositioned)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Closed Deals</div>
                        <div class="metric-value success">{ytd_stats['closed']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Close Rate</div>
                        <div class="metric-value success">{ytd_stats['close_rate']}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">KW Closed</div>
                        <div class="metric-value">{ytd_stats['kw']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Revenue</div>
                        <div class="metric-value">${ytd_stats['revenue']:,.0f}</div>
                    </div>
                    <div class="metric" style="grid-column: span 2;">
                        <div class="metric-label">States</div>
                        <div class="metric-value" style="font-size: 0.9em; line-height: 1.5;">{', '.join(ytd_stats['states'])}</div>
                    </div>
                </div>
            </div>

            <!-- MTD Card -->
            <div class="summary-card">
                <h2>📅 MTD (Month to Date)</h2>
                <p style="opacity: 0.7; margin-bottom: 15px; font-size: 0.9em;">{month_start} to {today}</p>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-label">Total Appointments</div>
                        <div class="metric-value info">{mtd_stats['total_appts']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Dispositioned</div>
                        <div class="metric-value" style="color: #ffa500;">{mtd_stats['dispositioned']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Sits</div>
                        <div class="metric-value info">{mtd_stats['sits']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Sit Rate</div>
                        <div class="metric-value success">{mtd_stats['sit_rate']}%</div>
                        <div style="font-size: 0.7em; opacity: 0.7;">(Sits/Dispositioned)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Closed Deals</div>
                        <div class="metric-value success">{mtd_stats['closed']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Close Rate</div>
                        <div class="metric-value success">{mtd_stats['close_rate']}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">KW Closed</div>
                        <div class="metric-value">{mtd_stats['kw']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Revenue</div>
                        <div class="metric-value">${mtd_stats['revenue']:,.0f}</div>
                    </div>
                    <div class="metric" style="grid-column: span 2;">
                        <div class="metric-label">States</div>
                        <div class="metric-value" style="font-size: 0.9em; line-height: 1.5;">{', '.join(mtd_stats['states'])}</div>
                    </div>
                </div>
            </div>

            <!-- WTD Card (Week to Date) -->
            <div class="summary-card">
                <h2>📊 WTD (Week to Date)</h2>
                <p style="opacity: 0.7; margin-bottom: 15px; font-size: 0.9em;">{week_start} to {today}</p>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-label">Total Appointments</div>
                        <div class="metric-value info">{wtd_stats['total_appts']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Dispositioned</div>
                        <div class="metric-value" style="color: #ffa500;">{wtd_stats['dispositioned']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Sits</div>
                        <div class="metric-value info">{wtd_stats['sits']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Sit Rate</div>
                        <div class="metric-value success">{wtd_stats['sit_rate']}%</div>
                        <div style="font-size: 0.7em; opacity: 0.7;">(Sits/Dispositioned)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Closed Deals</div>
                        <div class="metric-value success">{wtd_stats['closed']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Close Rate</div>
                        <div class="metric-value success">{wtd_stats['close_rate']}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">KW Closed</div>
                        <div class="metric-value">{wtd_stats['kw']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Revenue</div>
                        <div class="metric-value">${wtd_stats['revenue']:,.0f}</div>
                    </div>
                    <div class="metric" style="grid-column: span 2;">
                        <div class="metric-label">States</div>
                        <div class="metric-value" style="font-size: 0.9em; line-height: 1.5;">{', '.join(wtd_stats['states'])}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Monthly Breakdown Table -->
        <div class="monthly-section">
            <h2>📊 Per-Month Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Month</th>
                        <th>Appointments</th>
                        <th>Sits</th>
                        <th>Sit Rate</th>
                        <th>Closed</th>
                        <th>Close Rate</th>
                        <th>KW</th>
                        <th>Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    {monthly_rows}
                </tbody>
            </table>
        </div>

        <!-- Daily Averages -->
        <div class="daily-avg-section">
            <h2>📈 Daily Averages</h2>

            <!-- YTD Daily Averages -->
            <div style="margin-bottom: 30px;">
                <h3 style="font-size: 1.5em; margin-bottom: 20px; text-align: center; color: #60a5fa;">
                    📆 YTD Daily Averages ({ytd_daily_avgs['active_days']} active days)
                </h3>
                <div class="daily-grid">
                    <div class="daily-box">
                        <div class="label">Avg Appointments per Day</div>
                        <div class="value">{ytd_daily_avgs['daily_appts']}</div>
                    </div>
                    <div class="daily-box">
                        <div class="label">Avg Sits per Day</div>
                        <div class="value">{ytd_daily_avgs['daily_sits']}</div>
                    </div>
                    <div class="daily-box">
                        <div class="label">Avg Closed per Day</div>
                        <div class="value">{ytd_daily_avgs['daily_closed']}</div>
                    </div>
                </div>
            </div>

            <!-- MTD Daily Averages -->
            <div style="margin-bottom: 30px;">
                <h3 style="font-size: 1.5em; margin-bottom: 20px; text-align: center; color: #4ade80;">
                    📅 MTD Daily Averages ({mtd_daily_avgs['active_days']} active days)
                </h3>
                <div class="daily-grid">
                    <div class="daily-box">
                        <div class="label">Avg Appointments per Day</div>
                        <div class="value">{mtd_daily_avgs['daily_appts']}</div>
                    </div>
                    <div class="daily-box">
                        <div class="label">Avg Sits per Day</div>
                        <div class="value">{mtd_daily_avgs['daily_sits']}</div>
                    </div>
                    <div class="daily-box">
                        <div class="label">Avg Closed per Day</div>
                        <div class="value">{mtd_daily_avgs['daily_closed']}</div>
                    </div>
                </div>
            </div>

            <!-- WTD Daily Averages -->
            <div>
                <h3 style="font-size: 1.5em; margin-bottom: 20px; text-align: center; color: #fbbf24;">
                    📊 WTD Daily Averages ({wtd_daily_avgs['active_days']} active days)
                </h3>
                <div class="daily-grid">
                    <div class="daily-box">
                        <div class="label">Avg Appointments per Day</div>
                        <div class="value">{wtd_daily_avgs['daily_appts']}</div>
                    </div>
                    <div class="daily-box">
                        <div class="label">Avg Sits per Day</div>
                        <div class="value">{wtd_daily_avgs['daily_sits']}</div>
                    </div>
                    <div class="daily-box">
                        <div class="label">Avg Closed per Day</div>
                        <div class="value">{wtd_daily_avgs['daily_closed']}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Dashboard Info -->
        <div class="daily-avg-section">
            <h2>ℹ️ Dashboard Info</h2>
            <p style="opacity: 0.8; margin-bottom: 15px; text-align: center;">Real-time data from Podio for the Full Organization</p>

            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <p style="font-weight: bold; margin-bottom: 8px;">Time Periods:</p>
                <p style="font-size: 0.9em; margin: 5px 0;">
                    <strong style="color: #60a5fa;">YTD 2025:</strong> Jan 1, 2025 to today
                </p>
                <p style="font-size: 0.9em; margin: 5px 0;">
                    <strong style="color: #4ade80;">MTD:</strong> This month only
                </p>
                <p style="font-size: 0.9em; margin: 5px 0;">
                    <strong style="color: #fbbf24;">WTD:</strong> This week only
                </p>
            </div>

            <p style="opacity: 0.7; font-size: 0.9em;">
                <strong>Calculations:</strong><br>
                • Revenue: KW × 1000 × $5.50<br>
                • Sit Rate: Sits ÷ Appointments<br>
                • Close Rate: Closed ÷ Sits
            </p>
        </div>

        <!-- Monthly Breakdown Table -->
        <div class="monthly-section">
            <h2>📊 Per-Month Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Month</th>
                        <th>Appointments</th>
                        <th>Sits</th>
                        <th>Sit Rate</th>
                        <th>Closed</th>
                        <th>Close Rate</th>
                        <th>KW</th>
                        <th>Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    {monthly_rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p><strong>Full Organization Return Dashboard</strong> | Podio Closer App Data</p>
            <p>YTD 2025: {ytd_2025_start} to {today} | MTD: {month_start} to {today} | WTD: {week_start} to {today}</p>
            <p style="margin-top: 10px;">
                💰 Revenue Rate: $5.50/watt
            </p>
        </div>
    </div>

    <script>
        // Next refresh calculator and countdown timer
        function updateRefreshInfo() {{
            const now = new Date();
            const cronTimes = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]; // Hourly from 8am to 8pm

            // Find next refresh time
            let nextRefreshHour = null;
            const currentHour = now.getHours();

            // Find next cron time today
            for (let hour of cronTimes) {{
                if (hour > currentHour) {{
                    nextRefreshHour = hour;
                    break;
                }}
            }}

            // If no more cron times today, use first one tomorrow
            const nextRefresh = new Date(now);
            if (nextRefreshHour === null) {{
                nextRefresh.setDate(nextRefresh.getDate() + 1);
                nextRefreshHour = cronTimes[0];
            }}
            nextRefresh.setHours(nextRefreshHour, 0, 0, 0);

            // Calculate time difference
            const diff = nextRefresh - now;
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            // Format next refresh time
            const options = {{ hour: 'numeric', minute: '2-digit', hour12: true }};
            const timeStr = nextRefresh.toLocaleTimeString('en-US', options);
            const dateStr = nextRefresh.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }});

            // Update display
            document.getElementById('nextRefresh').textContent = `Next refresh: ${{timeStr}}`;
            document.getElementById('countdown').textContent = `Time until: ${{hours}}h ${{minutes}}m`;
        }}

        // Update immediately and then every second
        updateRefreshInfo();
        setInterval(updateRefreshInfo, 1000);
    </script>
</body>
</html>
"""

    output_path = "/Users/mosesherrera/Desktop/Podio Api Full Org/full_org_return.html"
    with open(output_path, "w") as f:
        f.write(html)

    print(f"✅ Dashboard saved: {output_path}")

def main():
    # Authenticate
    access_token = get_access_token()
    if not access_token:
        print("❌ Authentication failed. Exiting.")
        return

    # Fetch all data
    items = fetch_all_items(access_token)
    if not items:
        print("❌ No data fetched. Exiting.")
        return

    # Process appointments
    appointments_by_date = process_appointments(items)
    if not appointments_by_date:
        print("❌ No valid appointments found. Exiting.")
        return

    # Find YTD start (first day with 3+ appts or first appt)
    ytd_start = find_ytd_start(appointments_by_date)

    # Calculate "Since Start" stats (from first 3+ appt day)
    print("\n📊 Calculating 'Since Start' statistics...")
    since_start_appts = []
    for date, appts in appointments_by_date.items():
        if date >= ytd_start:
            since_start_appts.extend(appts)
    since_start_stats = calculate_metrics(since_start_appts)
    print(f"✅ Since Start ({ytd_start}): {since_start_stats['total_appts']} appts, {since_start_stats['closed']} closed, {since_start_stats['kw']} KW")

    # Calculate TRUE YTD (2025 only, exclude future appointments)
    print("\n📊 Calculating TRUE YTD (2025 only)...")
    today = datetime.now().date()
    ytd_2025_start = datetime(2025, 1, 1).date()
    ytd_appts = []
    for date, appts in appointments_by_date.items():
        if date >= ytd_2025_start and date <= today:
            ytd_appts.extend(appts)
    ytd_stats = calculate_metrics(ytd_appts)
    print(f"✅ YTD 2025: {ytd_stats['total_appts']} appts, {ytd_stats['closed']} closed, {ytd_stats['kw']} KW")

    # Calculate MTD stats (exclude future appointments)
    print("\n📊 Calculating MTD statistics...")
    today = datetime.now().date()
    month_start = today.replace(day=1)
    mtd_appts = []
    for date, appts in appointments_by_date.items():
        if date >= month_start and date <= today:
            mtd_appts.extend(appts)
    mtd_stats = calculate_metrics(mtd_appts)
    print(f"✅ MTD: {mtd_stats['total_appts']} appts, {mtd_stats['closed']} closed, {mtd_stats['kw']} KW")

    # Calculate WTD stats (Week to Date - Monday to today, exclude future appointments)
    print("\n📊 Calculating WTD statistics...")
    week_start = today - timedelta(days=today.weekday())  # Monday of current week
    wtd_appts = []
    for date, appts in appointments_by_date.items():
        if date >= week_start and date <= today:
            wtd_appts.extend(appts)
    wtd_stats = calculate_metrics(wtd_appts)
    print(f"✅ WTD (from {week_start}): {wtd_stats['total_appts']} appts, {wtd_stats['closed']} closed, {wtd_stats['kw']} KW")

    # Calculate monthly breakdown
    monthly_stats = calculate_monthly_stats(appointments_by_date, ytd_start)

    # Calculate daily averages (old method - keeping for compatibility)
    daily_avgs = calculate_daily_averages(appointments_by_date, ytd_start)
    print(f"✅ Daily averages: {daily_avgs['daily_appts']} appts/day, {daily_avgs['daily_closed']} closed/day")

    # Calculate daily averages based on ACTIVE days only
    print("\n📈 Calculating daily averages based on ACTIVE days (days with appointments)...")
    ytd_daily_avgs = calculate_daily_averages_active_days(appointments_by_date, ytd_2025_start, today)
    print(f"✅ YTD Daily Avgs: {ytd_daily_avgs['daily_appts']} appts/day over {ytd_daily_avgs['active_days']} active days")

    mtd_daily_avgs = calculate_daily_averages_active_days(appointments_by_date, month_start, today)
    print(f"✅ MTD Daily Avgs: {mtd_daily_avgs['daily_appts']} appts/day over {mtd_daily_avgs['active_days']} active days")

    wtd_daily_avgs = calculate_daily_averages_active_days(appointments_by_date, week_start, today)
    print(f"✅ WTD Daily Avgs: {wtd_daily_avgs['daily_appts']} appts/day over {wtd_daily_avgs['active_days']} active days")

    # Generate HTML
    generate_html(ytd_stats, since_start_stats, mtd_stats, wtd_stats, monthly_stats, daily_avgs, ytd_start, week_start, ytd_daily_avgs, mtd_daily_avgs, wtd_daily_avgs)

    print("\n" + "=" * 80)
    print("✅ FULL ORG RETURN DASHBOARD COMPLETE!")
    print("=" * 80)
    print(f"\n📍 Open the dashboard: full_org_return.html")

if __name__ == "__main__":
    main()
