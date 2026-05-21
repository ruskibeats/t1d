subagent
<longcat_arg_key>agent</longcat_arg_key>
<longcat_arg_value>scout</longcat_arg_value>
<longcat_arg_key>task</longcat_arg_key>
<longcat_arg_value>Clanker Ops #3: [GRAPH-C] Scout event-group API endpoint + auth for graph endpoints

Tags: #p1 #api #backend #graph
Branch: dad_1805

Scout the codebase at /root/t1d and report findings:
1. Is event_group_id used in ingestion flows (Fitbit, Garmin, manual meal/exercise/sleep)?
2. Does GET /api/v1/metrics/graph/event-group/{event_group_id} endpoint exist?
3. Do all graph endpoints use dependency-injected auth (require_active_user) or do any still use user_id query params?
4. Does graph_service.py have get_event_group() method?

Produce a concise findings summary at /root/t1d/scout-report-3.md

Work from /root/t1d.</longcat_arg_value>
<longcat_arg_key>async</longcat_arg_key>
<longcat_arg_value>true</longcat_arg_value>
<longcat_arg_key>context</longcat_arg_key>
<longcat_arg_value>fork</longcat_arg_value>
<longcat_arg_key>cwd</longcat_arg_key>
<longcat_arg_value>/root/t1d</longcat_arg_value>
</longcat_tool_call>
