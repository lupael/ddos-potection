# BGP Blackholing (RTBH) UI Layout

This document describes the layout and structure of the BGP Blackholing UI page.

## Page Layout Overview

```
┌────────────────────────────────────────────────────────────────────┐
│  🛡️ DDoS Protection Platform                                       │
│  [Dashboard] [Traffic] [Alerts] [Rules] [BGP/RTBH] [Reports] ...  │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  🛡️ BGP Blackholing (RTBH)              [➕ Announce Blackhole]   │
│  Remotely Triggered Black Hole - Drop attack traffic at ISP edge   │
└────────────────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│  Active          │  │  Total (24h)     │  │  Success Rate        │
│  Blackholes      │  │                  │  │                      │
│      5           │  │      23          │  │      87.5%           │
│  (red)           │  │  (blue)          │  │  (green/yellow)      │
└──────────────────┘  └──────────────────┘  └──────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  Announce BGP Blackhole (RTBH)                                     │
│                                                                    │
│  Select Alert *                                                    │
│  [Dropdown: #123 - syn_flood - 203.0.113.50 (critical)      ▼]   │
│                                                                    │
│  Prefix (CIDR) *                                                   │
│  [203.0.113.50/32                                            ]    │
│  IP address or network in CIDR notation. Use /32 for single IPv4  │
│                                                                    │
│  Next-hop (Optional)                                               │
│  [192.0.2.1                                                  ]    │
│  Blackhole next-hop IP (default: 192.0.2.1 from config)           │
│                                                                    │
│  Reason                                                            │
│  [DDoS attack - SYN flood                                    ]    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ ⚠️ Warning: Announcing a BGP blackhole will drop ALL       │ │
│  │ traffic to the specified prefix at your ISP's edge. Use    │ │
│  │ /32 for single IPs to minimize impact.                     │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  [🚨 Announce Blackhole]                                           │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  🔴 Active BGP Blackholes                                          │
├────┬──────────────┬─────────────┬──────────┬──────────┬───────────┤
│ ID │ Prefix       │ Alert Type  │ Severity │ Duration │ Actions   │
├────┼──────────────┼─────────────┼──────────┼──────────┼───────────┤
│ #5 │ 203.0.113.50 │ syn_flood   │ critical │ 2h 15m   │[Withdraw] │
│    │ /32          │             │  (red)   │          │           │
├────┼──────────────┼─────────────┼──────────┼──────────┼───────────┤
│ #4 │ 198.51.100.  │ udp_flood   │   high   │ 5h 42m   │[Withdraw] │
│    │ 200/32       │             │(orange)  │          │           │
└────┴──────────────┴─────────────┴──────────┴──────────┴───────────┘

┌────────────────────────────────────────────────────────────────────┐
│  📊 BGP Blackhole History (Last 24h)                               │
├────┬─────────────┬────────────┬──────────┬──────────┬─────────────┤
│ ID │ Alert Type  │ Target IP  │  Status  │ Duration │  Completed  │
├────┼─────────────┼────────────┼──────────┼──────────┼─────────────┤
│#23 │ syn_flood   │203.0.113.1 │completed │ 1h 23m   │ 2h ago      │
│    │             │            │ (green)  │          │             │
├────┼─────────────┼────────────┼──────────┼──────────┼─────────────┤
│#22 │ udp_flood   │198.51.100.5│completed │ 3h 15m   │ 5h ago      │
│    │             │            │ (green)  │          │             │
├────┼─────────────┼────────────┼──────────┼──────────┼─────────────┤
│#21 │ icmp_flood  │203.0.113.99│  failed  │   N/A    │ 6h ago      │
│    │             │            │  (red)   │          │             │
└────┴─────────────┴────────────┴──────────┴──────────┴─────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  ℹ️ About BGP Blackholing                                          │
│                                                                    │
│  BGP Blackholing (RTBH) is a DDoS mitigation technique that drops │
│  traffic at your ISP's edge routers before it reaches your        │
│  network.                                                          │
│                                                                    │
│  • Fast: Near-instant mitigation (1-5 seconds)                    │
│  • Bandwidth-saving: Stops attack traffic upstream                │
│  • Standard: Uses RFC 7999 blackhole community (65535:666)        │
│  • Automated: Can be triggered by detection systems               │
│                                                                    │
│  📖 For detailed setup instructions, see the BGP-RTBH             │
│     Documentation                                                  │
└────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Page Header
- **Title**: "🛡️ BGP Blackholing (RTBH)"
- **Subtitle**: Explains the purpose of RTBH
- **Action Button**: "➕ Announce Blackhole" - toggles the announcement form

### 2. Analytics Cards (3 cards in a row)
- **Card 1 - Active Blackholes**
  - Shows count of currently active blackhole routes
  - Red color to indicate critical/active state
  - Large font size for visibility
  
- **Card 2 - Total (24h)**
  - Shows total BGP blackholes in last 24 hours
  - Blue color for informational display
  
- **Card 3 - Success Rate**
  - Percentage of successful mitigations
  - Green if >80%, yellow/orange if lower
  - Indicates system reliability

### 3. Announcement Form (Collapsible)
Shows when "Announce Blackhole" button is clicked.

**Fields:**
- **Select Alert** (required): Dropdown populated with active alerts
  - Format: "#ID - alert_type - target_ip (severity)"
  
- **Prefix** (required): Text input for CIDR notation
  - Placeholder: "e.g., 203.0.113.50/32 or 2001:db8::1/128"
  - Help text explains CIDR usage
  
- **Next-hop** (optional): Text input for custom blackhole next-hop
  - Default value: 192.0.2.1 (from config)
  
- **Reason** (optional): Text input for audit trail
  - Example: "DDoS attack - SYN flood"

**Warning Box:**
- Yellow background with border
- ⚠️ icon
- Warns about traffic impact
- Emphasizes use of /32 for single IPs

**Submit Button:**
- "🚨 Announce Blackhole"
- Primary button style
- Triggers API call to create and execute mitigation

### 4. Active Blackholes Table
Real-time display of active BGP blackhole routes.

**Columns:**
- ID: Mitigation ID (#5, #4, etc.)
- Prefix: IP/CIDR in code block style
- Alert Type: Type of attack being mitigated
- Severity: Badge with color (critical=red, high=orange, medium=yellow, low=blue)
- Duration: Human-readable format (2h 15m, 5h 42m)
- Actions: "Withdraw" button - stops the blackhole

**Features:**
- Auto-refreshes every 30 seconds
- Empty state message if no active blackholes
- One-click withdraw with confirmation dialog

### 5. History Table
Shows last 24 hours of BGP blackhole mitigations.

**Columns:**
- ID: Mitigation ID
- Alert Type: Attack type
- Target IP: Protected IP address
- Status: Badge (completed=green, failed=red, active=yellow)
- Duration: How long the blackhole was active
- Completed: When the mitigation ended

**Features:**
- Filtered to show only BGP blackhole actions
- Color-coded status for quick scanning
- Shows null/N/A for incomplete data

### 6. Information Panel
Blue background informational card.

**Content:**
- Title: "ℹ️ About BGP Blackholing"
- Description of RTBH technology
- Bullet list of key benefits:
  - Fast mitigation
  - Bandwidth saving
  - Standard protocol
  - Automation capability
- Link to full documentation

## Color Scheme

- **Critical/Active**: Red (#e74c3c)
- **High Severity**: Orange (#f39c12)
- **Medium Severity**: Yellow (#f1c40f)
- **Low/Success**: Green (#27ae60)
- **Informational**: Blue (#3498db)
- **Inactive/Disabled**: Gray (#95a5a6)
- **Warning Background**: Light Yellow (#fff3cd)
- **Info Background**: Light Blue (#e3f2fd)

## User Flow

### Announcing a Blackhole
1. User clicks "➕ Announce Blackhole" button
2. Form expands/reveals
3. User selects an alert from dropdown (pre-populated with active alerts)
4. User enters prefix in CIDR notation
5. Optionally customizes next-hop and adds reason
6. User reads warning message
7. User clicks "🚨 Announce Blackhole"
8. System creates mitigation record
9. System executes BGP announcement
10. Success alert displays
11. Active blackholes table updates automatically
12. Form collapses and resets

### Withdrawing a Blackhole
1. User finds active blackhole in table
2. User clicks "Withdraw" button
3. Confirmation dialog appears
4. User confirms action
5. System withdraws BGP route
6. Success alert displays
7. Row removed from active table
8. Row added to history table with "completed" status

### Auto-refresh
- Page data refreshes every 30 seconds automatically
- Keeps active blackholes and statistics current
- No user interaction needed
- Ensures operators see latest state

## Responsive Design

The UI is fully responsive:
- Analytics cards stack vertically on mobile
- Tables become scrollable horizontally on small screens
- Form fields stack on mobile
- Navigation menu collapses on small screens

## Accessibility

- Semantic HTML elements
- Color is not the only indicator (uses text labels)
- Keyboard navigation support
- ARIA labels where appropriate
- High contrast text
- Clear focus indicators
