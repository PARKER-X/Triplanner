import time
import math
from typing import List, Dict, Any
from .schema import OptimizedActivity, OptimizedDayPlan, OptimizationStats, OptimizationResult

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

class OptimizerAgent:
    def __init__(self):
        print('✅ Optimizer Agent initialized (Two-Stage: DP + Local Search)')

    def _extract_coords(self, activity_dict):
        if 'coordinates' in activity_dict:
            return activity_dict['coordinates'].get('lat', 0), activity_dict['coordinates'].get('lng', 0)
        return 0, 0

    def _resequence_activities(self, activities: List[Dict]) -> List[Dict]:
        if not activities:
            return []
        unvisited = list(activities)
        current = unvisited.pop(0)
        sequence = [current]
        
        while unvisited:
            curr_lat, curr_lon = self._extract_coords(current)
            best_idx = 0
            best_dist = float('inf')
            
            for i, act in enumerate(unvisited):
                lat, lon = self._extract_coords(act)
                dist = haversine(curr_lat, curr_lon, lat, lon)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
                    
            current = unvisited.pop(best_idx)
            sequence.append(current)
            
        return sequence

    def _mins_to_str(self, mins: int) -> str:
        h = int(mins // 60)
        m = int(mins % 60)
        return f"{h:02d}:{m:02d}"

    def _recalculate_times(self, activities: List[Dict]) -> List[Dict]:
        current_time_mins = 9 * 60
        result = []
        for i, act in enumerate(activities):
            start_time = current_time_mins
            duration = act.get('duration_minutes', 60)
            end_time = start_time + duration
            
            travel_time = 0
            if i < len(activities) - 1:
                next_act = activities[i+1]
                lat1, lon1 = self._extract_coords(act)
                lat2, lon2 = self._extract_coords(next_act)
                dist = haversine(lat1, lon1, lat2, lon2)
                travel_time = 15 if dist <= 3.0 else 30
            
            # Must fit in 9-21 window
            if end_time <= 21 * 60:
                act_copy = dict(act)
                act_copy['time_start'] = self._mins_to_str(start_time)
                act_copy['time_end'] = self._mins_to_str(end_time)
                act_copy['travel_time_to_next'] = travel_time
                act_copy['sequence'] = i + 1
                result.append(act_copy)
                current_time_mins = end_time + travel_time
            else:
                break
                
        return result

    def _score_day(self, activities: List[Dict]) -> float:
        if not activities:
            return 0.0
        
        feasibility = 1.0 
        
        categories = set(a.get('category', 'unknown') for a in activities)
        variety = len(categories) / max(1, len(activities))
        
        quality = sum(a.get('rating', 4.0) for a in activities) / len(activities) / 5.0
        
        return 0.3 * feasibility + 0.4 * variety + 0.3 * quality

    def run(self, planning_state) -> OptimizationResult:
        if not hasattr(planning_state, 'selected_plan') or not planning_state.selected_plan:
            return OptimizationResult(
                days=[],
                stats=OptimizationStats(total_swaps=0, score_improvement_pct=0.0, stages_completed=0, intra_day_time_ms=0, inter_day_time_ms=0),
                total_score=0.0,
                is_feasible=False,
                warnings=["No selected plan found"]
            )
            
        plan_dict = planning_state.selected_plan
        days = plan_dict.get('days', [])
        
        # STAGE 1: Intra-Day Optimization
        t0 = time.time()
        stage1_days = []
        for day in days:
            acts = day.get('activities', [])
            reseq = self._resequence_activities(acts)
            timed = self._recalculate_times(reseq)
            score = self._score_day(timed)
            stage1_days.append({
                'day_number': day.get('day_number', 1),
                'theme': day.get('theme', ''),
                'total_cost': day.get('total_cost', 0.0),
                'total_walking_km': day.get('total_walking_km', 0.0),
                'activities': timed,
                'feasibility_score': score
            })
        intra_day_time_ms = (time.time() - t0) * 1000

        # STAGE 2: Inter-Day Optimization
        t1 = time.time()
        
        initial_score = sum(d['feasibility_score'] for d in stage1_days)
        total_swaps = 0
        
        for iteration in range(50):
            improved = False
            for i in range(len(stage1_days)):
                for j in range(i + 1, len(stage1_days)):
                    day_i = stage1_days[i]
                    day_j = stage1_days[j]
                    
                    for idx_i in range(len(day_i['activities'])):
                        for idx_j in range(len(day_j['activities'])):
                            acts_i = list(day_i['activities'])
                            acts_j = list(day_j['activities'])
                            
                            # Swap
                            acts_i[idx_i], acts_j[idx_j] = acts_j[idx_j], acts_i[idx_i]
                            
                            # Recalculate
                            timed_i = self._recalculate_times(self._resequence_activities(acts_i))
                            timed_j = self._recalculate_times(self._resequence_activities(acts_j))
                            
                            score_i = self._score_day(timed_i)
                            score_j = self._score_day(timed_j)
                            
                            new_sum = score_i + score_j
                            old_sum = day_i['feasibility_score'] + day_j['feasibility_score']
                            
                            if new_sum > old_sum:
                                day_i['activities'] = timed_i
                                day_i['feasibility_score'] = score_i
                                day_j['activities'] = timed_j
                                day_j['feasibility_score'] = score_j
                                improved = True
                                total_swaps += 1
                                break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
            
            if not improved:
                break
                
        inter_day_time_ms = (time.time() - t1) * 1000
        
        final_score = sum(d['feasibility_score'] for d in stage1_days)
        score_improvement_pct = 0.0
        if initial_score > 0:
            score_improvement_pct = ((final_score - initial_score) / initial_score) * 100
            
        opt_days = []
        for d in stage1_days:
            opt_acts = []
            for act in d['activities']:
                opt_acts.append(OptimizedActivity(
                    sequence=act.get('sequence', 0),
                    time_start=act.get('time_start', ''),
                    time_end=act.get('time_end', ''),
                    activity_id=act.get('activity_id', ''),
                    activity_name=act.get('activity_name', act.get('name', 'Unknown')),
                    category=act.get('category', 'unknown'),
                    location=act.get('location', ''),
                    address=act.get('address', ''),
                    cost_per_person=act.get('cost_per_person', 0.0),
                    duration_minutes=act.get('duration_minutes', 60),
                    description=act.get('description', ''),
                    why_included=act.get('why_included', ''),
                    travel_time_to_next=act.get('travel_time_to_next', 0)
                ))
                
            opt_days.append(OptimizedDayPlan(
                day_number=d['day_number'],
                theme=d['theme'],
                activities=opt_acts,
                total_cost=d['total_cost'],
                total_walking_km=d['total_walking_km'],
                feasibility_score=d['feasibility_score']
            ))
            
        stats = OptimizationStats(
            total_swaps=total_swaps,
            score_improvement_pct=score_improvement_pct,
            stages_completed=2,
            intra_day_time_ms=intra_day_time_ms,
            inter_day_time_ms=inter_day_time_ms
        )
        
        result = OptimizationResult(
            days=opt_days,
            stats=stats,
            total_score=final_score,
            is_feasible=True,
            warnings=[]
        )
        
        if hasattr(planning_state, 'optimization_result'):
            planning_state.optimization_result = result.model_dump()
        else:
            setattr(planning_state, 'optimization_result', result.model_dump())

        # Merge display fields from selected_plan so summary stats show correctly
        if planning_state.optimization_result and planning_state.selected_plan:
            sp = planning_state.selected_plan
            planning_state.optimization_result["trip_title"] = sp.get("trip_title", "Trip Itinerary")
            planning_state.optimization_result["trip_summary"] = sp.get("trip_summary", "")
            planning_state.optimization_result["stats"] = sp.get("stats", {})
            planning_state.optimization_result["highlights"] = sp.get("highlights", [])
            planning_state.optimization_result["tips"] = sp.get("tips", [])
            planning_state.optimization_result["warnings"] = sp.get("warnings", [])

        return result
