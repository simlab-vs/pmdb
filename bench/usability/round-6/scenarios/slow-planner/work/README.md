# routeplan

Plans the next day's delivery routes for the depot's vans and small trucks.

    python3 plan_day.py data/orders_2026-09-28.json --fleet data/fleet.json -o out/

Input: the day's orders (stop coordinates in km from the city centre, kg, service minutes and an
optional delivery window in minutes after 07:00) and the fleet (vehicle kinds with capacity and
costs). Output, in the output directory: `routes_<date>.tsv`, one line per vehicle used with its
stops in order, and `summary_<date>.txt`, also printed. The planner checks the final plan from
scratch and lists any problem in the summary; the exit status is 1 if there is one.

How it plans: savings construction, then a descent over five neighbourhoods (relocate, swap,
segment move, tail exchange, 2-opt), restarted `--rounds` times from partly ruined and
recreated plans, and finally an attempt to take the lightest routes out of service.
A full day (about 1,200 stops) takes a few minutes.
