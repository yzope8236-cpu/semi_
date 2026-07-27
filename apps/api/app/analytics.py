from fastapi import APIRouter, HTTPException
from .db import rows

router = APIRouter(tags=["Analytics"])

@router.get('/api/v1/analytics/wafers/{wafer_id}/summary')
def wafer_summary(wafer_id: str):
    wafer = rows("SELECT wafer_id, lot_id FROM wafers WHERE wafer_id={w:String} LIMIT 1", {'w':wafer_id})
    if not wafer: raise HTTPException(404, 'Wafer not found')
    
    # Calculate summary from final devices
    metrics = rows("""
        SELECT count() total_dies, sum(passed) pass_count, sum(passed=0) fail_count, 
        round(avg(passed)*100,2) yield_pct, round(sum(passed=0)*1000000/count(),0) dppm,
        sum(retest_count > 0) retest_count, round(sum(retest_count > 0)*100/count(),2) retest_rate_pct
        FROM devices FINAL WHERE wafer_id={w:String} AND is_final_attempt=1
    """, {'w':wafer_id})[0]
    
    # Distributions
    hbins = rows("SELECT hardware_bin as bin, count() count FROM devices FINAL WHERE wafer_id={w:String} AND is_final_attempt=1 GROUP BY hardware_bin ORDER BY count DESC", {'w':wafer_id})
    sbins = rows("SELECT software_bin as bin, count() count FROM devices FINAL WHERE wafer_id={w:String} AND is_final_attempt=1 GROUP BY software_bin ORDER BY count DESC", {'w':wafer_id})
    sites = rows("SELECT site, count() count FROM devices FINAL WHERE wafer_id={w:String} AND is_final_attempt=1 GROUP BY site ORDER BY count DESC", {'w':wafer_id})
    
    top_tests = rows("""
        SELECT t.test_num, t.test_name, count() observations, sum(t.passed=0) failures, round(sum(t.passed=0)*100/count(),2) failure_rate 
        FROM test_results t INNER JOIN devices d USING (device_id, wafer_id)
        WHERE t.wafer_id={w:String} AND d.is_final_attempt=1
        GROUP BY t.test_num, t.test_name
        HAVING failures > 0
        ORDER BY failures DESC LIMIT 5
    """, {'w':wafer_id})
    
    return {
        'wafer_id': wafer_id,
        'lot_id': wafer[0]['lot_id'],
        **metrics,
        'hardware_bin_distribution': hbins,
        'software_bin_distribution': sbins,
        'site_distribution': sites,
        'top_failing_tests': top_tests
    }

@router.get('/api/v1/analytics/wafers/{wafer_id}/tests')
def wafer_tests(wafer_id: str):
    wafer = rows("SELECT wafer_id FROM wafers WHERE wafer_id={w:String} LIMIT 1", {'w':wafer_id})
    if not wafer: raise HTTPException(404, 'Wafer not found')
    return rows("""
        SELECT t.test_num, t.test_name, max(t.normalized_unit) units, count() observation_count, sum(t.passed=0) fail_count,
        round(sum(t.passed=0)*100/count(),2) failure_rate, avg(t.measured_value) average_value, min(t.measured_value) minimum_value,
        max(t.measured_value) maximum_value, any(t.lower_limit) lower_limit, any(t.upper_limit) upper_limit
        FROM test_results t INNER JOIN devices d USING (device_id, wafer_id)
        WHERE t.wafer_id={w:String} AND d.is_final_attempt=1
        GROUP BY t.test_num, t.test_name ORDER BY fail_count DESC
    """, {'w':wafer_id})

@router.get('/api/v1/analytics/wafers/{wafer_id}/sites')
def wafer_sites(wafer_id: str):
    wafer = rows("SELECT wafer_id FROM wafers WHERE wafer_id={w:String} LIMIT 1", {'w':wafer_id})
    if not wafer: raise HTTPException(404, 'Wafer not found')
    return rows("""
        SELECT site, count() tested_dies, sum(passed=0) failed_dies, round(avg(passed)*100,2) yield_pct, sum(retest_count) retest_count,
        any(hardware_bin) top_hardware_bin
        FROM devices FINAL WHERE wafer_id={w:String} AND is_final_attempt=1
        GROUP BY site ORDER BY site
    """, {'w':wafer_id})

@router.get('/api/v1/analytics/wafers/{wafer_id}/retests')
def wafer_retests(wafer_id: str):
    wafer = rows("SELECT wafer_id FROM wafers WHERE wafer_id={w:String} LIMIT 1", {'w':wafer_id})
    if not wafer: raise HTTPException(404, 'Wafer not found')
    
    groupings = rows("""
        SELECT site, x_coord, y_coord, count() attempts, min(passed) first_pass, argMax(passed, tested_at) final_pass
        FROM devices FINAL WHERE wafer_id={w:String}
        GROUP BY site, x_coord, y_coord
    """, {'w':wafer_id})
    
    total_attempts = sum(g['attempts'] for g in groupings)
    physical_devices = len(groupings)
    retested_devices = sum(1 for g in groupings if g['attempts'] > 1)
    first_attempt_pass = sum(1 for g in groupings if g.get('first_pass', 0) == 1)
    final_pass = sum(1 for g in groupings if g.get('final_pass', 0) == 1)
    recovered = sum(1 for g in groupings if g.get('first_pass', 0) == 0 and g.get('final_pass', 0) == 1)
    unrecovered = sum(1 for g in groupings if g.get('first_pass', 0) == 0 and g.get('final_pass', 0) == 0)
    recovery_rate = round(recovered*100/(recovered+unrecovered), 2) if (recovered+unrecovered)>0 else 0.0
    
    history = rows("SELECT device_id, site, x_coord, y_coord, hardware_bin, passed, retest_count FROM devices FINAL WHERE wafer_id={w:String} ORDER BY y_coord, x_coord, retest_count", {'w':wafer_id})
    
    return {
        'total_attempts': total_attempts,
        'physical_devices': physical_devices,
        'retested_devices': retested_devices,
        'first_attempt_pass_count': first_attempt_pass,
        'final_pass_count': final_pass,
        'recovered_devices': recovered,
        'unrecovered_devices': unrecovered,
        'recovery_rate_pct': recovery_rate,
        'history': history
    }

@router.get('/api/v1/analytics/wafer-comparison')
def wafer_comparison(left: str, right: str):
    if not left or not right or left == right:
        raise HTTPException(400, 'Invalid comparison parameters')
        
    left_wafer = rows("SELECT wafer_id FROM wafers WHERE wafer_id={w:String} LIMIT 1", {'w':left})
    right_wafer = rows("SELECT wafer_id FROM wafers WHERE wafer_id={w:String} LIMIT 1", {'w':right})
    if not left_wafer or not right_wafer:
        raise HTTPException(404, 'One or both wafers not found')
        
    def get_summary(wid):
        return rows("""
            SELECT count() total_dies, round(avg(passed)*100,2) yield_pct, sum(passed=0) fail_count,
            round(sum(passed=0)*1000000/count(),0) dppm FROM devices FINAL WHERE wafer_id={w:String} AND is_final_attempt=1
        """, {'w':wid})[0]
        
    def get_failures(wid):
        return rows("""
            SELECT t.test_name, round(sum(t.passed=0)*100/count(),2) failure_rate 
            FROM test_results t INNER JOIN devices d USING (device_id, wafer_id)
            WHERE t.wafer_id={w:String} AND d.is_final_attempt=1
            GROUP BY t.test_name
            HAVING sum(t.passed=0) > 0
            ORDER BY failure_rate DESC LIMIT 5
        """, {'w':wid})

    l_sum = get_summary(left)
    r_sum = get_summary(right)
    
    return {
        'left': left,
        'right': right,
        'left_summary': l_sum,
        'right_summary': r_sum,
        'yield_delta_pct': round(l_sum['yield_pct'] - r_sum['yield_pct'], 2),
        'fail_delta': l_sum['fail_count'] - r_sum['fail_count'],
        'dppm_delta': l_sum['dppm'] - r_sum['dppm'],
        'left_failures': get_failures(left),
        'right_failures': get_failures(right)
    }

@router.get('/api/v1/analytics/conclusions')
def conclusions():
    results = []
    
    wafers = rows("""
        SELECT wafer_id, lot_id, count() devices, round(avg(passed)*100,2) yield_pct
        FROM devices FINAL WHERE is_final_attempt=1 GROUP BY wafer_id, lot_id
    """)
    if not wafers:
        return results
        
    sorted_w = sorted(wafers, key=lambda x: x['yield_pct'])
    worst = sorted_w[0]
    best = sorted_w[-1]
    
    if worst['wafer_id'] != best['wafer_id']:
        results.append({
            'severity': 'info', 'category': 'yield', 'title': 'Baseline Yield Comparison',
            'message': f"Wafer {worst['wafer_id']} ({worst['yield_pct']}%) underperforms best-in-class wafer {best['wafer_id']} ({best['yield_pct']}%).",
            'evidence': f"Yield delta is {round(best['yield_pct'] - worst['yield_pct'], 2)}%",
            'affected_lot': worst['lot_id'], 'affected_wafer': worst['wafer_id'],
            'recommended_action': "Compare test failure pareto between these wafers.",
            'data_scope': 'synthetic_fixture_comparison'
        })
        
    for w in wafers:
        wid = w['wafer_id']
        lot = w['lot_id']
        y_pct = w['yield_pct']
        
        if y_pct < 90.0:
            results.append({
                'severity': 'critical', 'category': 'yield', 'title': 'Critical Yield Loss',
                'message': f"Evidence suggests critical yield loss on wafer {wid}.",
                'evidence': f"Yield is {y_pct}% (<90%)",
                'affected_lot': lot, 'affected_wafer': wid,
                'recommended_action': "Candidate investigation area: immediately review test bin pareto.",
                'data_scope': 'synthetic_fixture_comparison'
            })
        elif y_pct < 95.0:
            results.append({
                'severity': 'warning', 'category': 'yield', 'title': 'Low Yield Warning',
                'message': f"Observed pattern of low yield on wafer {wid}.",
                'evidence': f"Yield is {y_pct}% (<95%)",
                'affected_lot': lot, 'affected_wafer': wid,
                'recommended_action': "Recommended engineering review of spatial map.",
                'data_scope': 'synthetic_fixture_comparison'
            })
            
        edge = rows("""
            SELECT count() failed, sum(x_coord IN (0,9) OR y_coord IN (0,9)) edge_failed 
            FROM devices FINAL WHERE wafer_id={w:String} AND passed=0 AND is_final_attempt=1
        """, {'w':wid})[0]
        if edge['failed'] > 0 and (edge['edge_failed']/edge['failed']) >= 0.5:
            results.append({
                'severity': 'warning', 'category': 'spatial', 'title': 'Edge-Dominant Failure Pattern',
                'message': f"Evidence suggests edge-dominant failures on wafer {wid}.",
                'evidence': f"{round(edge['edge_failed']*100/edge['failed'],1)}% of failures are on wafer edge.",
                'affected_lot': lot, 'affected_wafer': wid,
                'recommended_action': "Candidate investigation area: check processing tool uniformity.",
                'data_scope': 'synthetic_fixture_comparison'
            })
            
        tests = rows("""
            SELECT t.test_name, count() observations, sum(t.passed=0) failures, round(sum(t.passed=0)*100/count(),2) failure_rate 
            FROM test_results t INNER JOIN devices d USING (device_id, wafer_id)
            WHERE t.wafer_id={w:String} AND d.is_final_attempt=1
            GROUP BY t.test_name
            HAVING failures > 0
        """, {'w':wid})
        high_impact = [t for t in tests if t['observations'] >= 3 and t['failure_rate'] >= 10.0]
        if high_impact:
            top_test = sorted(high_impact, key=lambda x: (x['failure_rate'], x['failures']), reverse=True)[0]
            results.append({
                'severity': 'warning', 'category': 'test', 'title': f"High Impact Test: {top_test['test_name']}",
                'message': f"Observed pattern of frequent failures for test {top_test['test_name']}.",
                'evidence': f"Test failure rate is {top_test['failure_rate']}% (>10% with >=3 observations).",
                'affected_lot': lot, 'affected_wafer': wid,
                'recommended_action': "Recommended engineering review of test parameter limits.",
                'data_scope': 'synthetic_fixture_comparison'
            })
            
        sites = rows("SELECT site, count() dies, round(avg(passed)*100,2) yield_pct FROM devices FINAL WHERE wafer_id={w:String} AND is_final_attempt=1 GROUP BY site", {'w':wid})
        if sites and len(sites) >= 2:
            avg_y = sum(s['yield_pct'] for s in sites) / len(sites)
            worst_site = max(sites, key=lambda s: abs(s['yield_pct'] - avg_y))
            if abs(worst_site['yield_pct'] - avg_y) > 5.0:
                results.append({
                    'severity': 'warning', 'category': 'site', 'title': 'Site Imbalance',
                    'message': f"Evidence suggests site {worst_site['site']} yield deviates materially.",
                    'evidence': f"Site {worst_site['site']} yield ({worst_site['yield_pct']}%) differs from mean ({round(avg_y,1)}%).",
                    'affected_lot': lot, 'affected_wafer': wid,
                    'recommended_action': "Candidate investigation area: verify site hardware/probe card.",
                    'data_scope': 'synthetic_fixture_comparison'
                })
                    
        retest = rows("""
            SELECT count() devices, min(passed) first_pass, argMax(passed, tested_at) final_pass
            FROM devices FINAL WHERE wafer_id={w:String}
            GROUP BY site, x_coord, y_coord HAVING count() > 1
        """, {'w':wid})
        if retest:
            recovered = sum(1 for r in retest if r.get('first_pass', 0) == 0 and r.get('final_pass', 0) == 1)
            unrecovered = sum(1 for r in retest if r.get('first_pass', 0) == 0 and r.get('final_pass', 0) == 0)
            if unrecovered > 0:
                results.append({
                    'severity': 'warning', 'category': 'retest', 'title': 'Unrecovered Retests',
                    'message': f"Evidence suggests retests are failing to recover yield on {wid}.",
                    'evidence': f"{unrecovered} devices remained failed after retest.",
                    'affected_lot': lot, 'affected_wafer': wid,
                    'recommended_action': "Recommended engineering review to avoid wasted retest time.",
                    'data_scope': 'synthetic_fixture_comparison'
                })
            elif recovered > 0:
                results.append({
                    'severity': 'info', 'category': 'retest', 'title': 'Retest Recovery Identified',
                    'message': f"Observed pattern of successful recovery via retest on {wid}.",
                    'evidence': f"{recovered} devices recovered.",
                    'affected_lot': lot, 'affected_wafer': wid,
                    'recommended_action': "Review if first-pass limit or hardware stability is acceptable.",
                    'data_scope': 'synthetic_fixture_comparison'
                })

    return results
