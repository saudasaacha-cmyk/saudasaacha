1- sudo systemctl restart saudasaacha-backend

repo - cd /opt/saudasaacha

2 -sudo systemctl is-active saudasaacha-backend

3. check_user CL49966876
4. check_user CL65758646 2026-06-18

5. sudo systemctl restart saudasaacha-backend

6- cd /root/sachchasauda/frontend-user && npm install && npm run build && pm2 restart saudasaacha-user
cd /root/sachchasauda/frontend-admin && npm install && npm run build && pm2 restart saudasaacha-admin
cd /root/sachchasauda && sudo systemctl restart saudasaacha-backend


journalctl -u saudasaacha-backend --since "1 min ago" --no-pager | grep -E "risk_enforcer_perf|tick_overrun" | grep -oE '"total_ms": [0-9.]+|"sweep_ms": [0-9.]+' | paste - - | tail -8; \
ps -eo pcpu,pid,comm --sort=-pcpu | head -4; \
for i in 1 2 3; do curl -s -o /dev/null -w "health: %{http_code} %{time_total}s\n" http://127.0.0.1:8000/health; done


logs ke liye - journalctl -u saudasaacha-backend --since "today" --no-pager | grep -E "stop_out_triggered|risk_outlier_tick_skipped|risk_ltp_fetch_failed|squareoff" | tail -40


perfomace ---

 echo "========== SYSTEM =========="; uptime; free -h | head -2; echo "Workers (chahiye 6): $(ps -ef | grep -c '[g]unicorn')  | Service: $(systemctl is-active saudasaacha-backend)"; \
echo ""; echo "========== API SPEED =========="; curl -o /dev/null -s -w "API: HTTP %{http_code} in %{time_total}s\n" http://127.0.0.1:8000/api/v1/health; \
echo ""; echo "========== RISK TIMING (30 min) =========="; echo "Overruns: $(journalctl -u saudasaacha-backend --since '30 min ago' --no-pager | grep -c tick_overrun)  (kam = achha)"; journalctl -u saudasaacha-backend --since '30 min ago' --no-pager | grep tick_overrun | grep -oE '"elapsed_sec": [0-9.]+' | tail -5; \
echo ""; echo "========== ERRORS (30 min) =========="; echo "Errors: $(journalctl -u saudasaacha-backend --since '30 min ago' --no-pager | grep -c '\"level\": \"ERROR\"')"; journalctl -u saudasaacha-backend --since '30 min ago' --no-pager | grep '\"level\": \"ERROR\"' | grep -oE '\"message\": \"[^\"]+\"' | sort | uniq -c | sort -rn | head -5; \
echo ""; echo "========== STOP-OUT / SL / TP (aaj) =========="; journalctl -u saudasaacha-backend --since '09:00:00' --no-pager | grep -iE "stop_out_triggered|risk_auto_squareoff|sl_hit|tp_hit" | tail -8; \
echo ""; echo "========== FEED / SPREAD (aaj) =========="; echo "Stale feed events: $(journalctl -u saudasaacha-backend --since '09:00:00' --no-pager | grep -cE 'no live session|risk_ltp_fetch_failed|ws_dead')"; journalctl -u saudasaacha-backend --since '09:00:00' --no-pager | grep -iE "no live session|ws_dead|reconnect|resubscribe" | tail -5; \
echo ""; echo "========== CPU TOP 5 =========="; ps -eo pcpu,pmem,comm --sort=-pcpu | head -6

journalctl -u saudasaacha-backend --since '10 hours ago' --no-pager | grep -iE "stop_out_triggered|risk_auto_squareoff|sl_hit|tp_hit" | tail -8



