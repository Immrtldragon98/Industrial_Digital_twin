# Data requested for the pilot

Minimum first upload: equipment hierarchy plus 6–12 months of notification/order history for one pilot area.

## Asset master

- Plant, department, area and functional-location codes
- Equipment number, name, type and parent equipment number
- Sub-equipment/component list
- Manufacturer, model, serial number, installation/commissioning date
- Criticality and production consequence

## SAP PM exports

- Notifications: number, equipment, dates, breakdown flag, malfunction duration, damage/cause/activity codes, short and long text
- Orders: number/type, equipment, planned/actual dates, operation text, work centre, labour, status, cost and technical completion date
- Measurement documents/points: equipment, measuring point, characteristic, timestamp, value and unit
- Maintenance plans/items/call history, task lists and equipment history card

## Actual condition and context

- Parameter list: vibration, temperature, pressure, flow, current, speed, level, leakage, clearance and oil condition as applicable
- Normal/warning/critical limits, units and sampling frequency
- Operating hours, production tonnes, starts/stops and planned shutdown hours
- Manual inspection/checksheet history

## Reliability knowledge

- RCA/RCFA, FMEA/FMECA, RCM and bad-actor reports
- PM task lists, SOPs, OEM manuals, datasheets and troubleshooting guides
- Mechanical/electrical/hydraulic/pneumatic drawings
- BOM, spares consumption, stock, PR and PO data for later spare optimization

## Decisions needed

1. Pilot equipment/area and date range.
2. Failure definition: corrective notifications, breakdowns only, or plant rule.
3. MTBF basis: calendar hours, running hours or production hours.
4. Planned downtime treatment in availability.
5. Roles: admin, planner, maintainer, operator and viewer.
6. Deployment: plant PC/server, company network or cloud.
7. Whether documents may leave the plant network; if not, AI stays fully local.
