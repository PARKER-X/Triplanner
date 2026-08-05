from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from .schema import Violation, CriticVerdict

class CriticAgent:
    def __init__(self, llm=None):
        self.rules = [
            'budget_check',
            'time_window_check', 
            'travel_sanity_check',
            'duplicate_check',
            'rest_check',
            'meal_gap_check',
            'empty_day_check'
        ]
        print('✅ Critic Agent initialized (7 validation rules)')
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        if not time_str:
            return None
        try:
            return datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return None

    def run(self, planning_state) -> CriticVerdict:
        violations: List[Violation] = []
        
        print("🔍 Critic Agent running deterministic validation...")
        
        # Get the plan to validate — these are dicts, not objects
        plan_days = []
        try:
            opt_result = planning_state.optimization_result
            if opt_result and isinstance(opt_result, dict) and opt_result.get('days'):
                plan_days = opt_result['days']
            elif planning_state.selected_plan and isinstance(planning_state.selected_plan, dict):
                plan_days = planning_state.selected_plan.get('days', [])
        except Exception as e:
            print(f"⚠️ Error extracting plan days: {e}")
            
        # Extract budget using helper
        budget = 0.0
        try:
            budget = planning_state.get_budget()
        except Exception:
            pass

        # Rule 1: BUDGET CHECK
        try:
            print("💰 Running budget_check...")
            if budget > 0 and plan_days:
                total_cost = sum(getattr(day, 'total_cost', 0.0) for day in plan_days)
                if total_cost > budget:
                    over_percent = ((total_cost - budget) / budget) * 100
                    if over_percent > 10:
                        violations.append(Violation(
                            rule='budget_check',
                            severity='critical',
                            details=f"Total cost ₹{total_cost} exceeds budget ₹{budget} by >10%.",
                            suggested_fix="Remove expensive activities or replace them."
                        ))
                    else:
                        violations.append(Violation(
                            rule='budget_check',
                            severity='warning',
                            details=f"Total cost ₹{total_cost} exceeds budget ₹{budget} by <=10%.",
                            suggested_fix="Try to reduce costs slightly."
                        ))
        except Exception as e:
            print(f"⚠️ Error in budget_check: {e}")

        # Day-level and Activity-level checks
        all_activities = []
        for i, day in enumerate(plan_days):
            day_num = day.get('day_number', i + 1) if isinstance(day, dict) else getattr(day, 'day_number', i + 1)
            activities = day.get('activities', []) if isinstance(day, dict) else getattr(day, 'activities', [])
            
            # Rule 7: EMPTY DAY CHECK
            try:
                print(f"📅 Running empty_day_check for Day {day_num}...")
                if len(activities) == 0:
                    violations.append(Violation(
                        rule='empty_day_check',
                        severity='critical',
                        details=f"Day {day_num} has 0 activities.",
                        affected_day=day_num,
                        suggested_fix="Add activities to this empty day."
                    ))
                elif len(activities) == 1:
                    violations.append(Violation(
                        rule='empty_day_check',
                        severity='warning',
                        details=f"Day {day_num} has only 1 activity.",
                        affected_day=day_num,
                        suggested_fix="Consider adding more activities to utilize the day."
                    ))
            except Exception as e:
                print(f"⚠️ Error in empty_day_check for Day {day_num}: {e}")

            # Rule 3: TRAVEL SANITY CHECK
            try:
                print(f"🚶 Running travel_sanity_check for Day {day_num}...")
                walking_km = day.get('total_walking_km', 0.0) if isinstance(day, dict) else getattr(day, 'total_walking_km', 0.0)
                if walking_km >= 35.0:
                    violations.append(Violation(
                        rule='travel_sanity_check',
                        severity='critical',
                        details=f"Total walking distance {walking_km}km on Day {day_num} is too high.",
                        affected_day=day_num,
                        suggested_fix="Reduce walking by grouping nearby activities."
                    ))
                elif walking_km >= 25.0:
                    violations.append(Violation(
                        rule='travel_sanity_check',
                        severity='warning',
                        details=f"Total walking distance {walking_km}km on Day {day_num} is high.",
                        affected_day=day_num,
                        suggested_fix="Consider adding transit options."
                    ))
            except Exception as e:
                print(f"⚠️ Error in travel_sanity_check for Day {day_num}: {e}")

            # Collect activities for trip-wide checks
            categories_today = {}
            last_meal_time = self._parse_time("09:00") # Assume day starts with meal
            
            for act in activities:
                all_activities.append(act)
                
                name = act.get('activity_name', '') if isinstance(act, dict) else getattr(act, 'activity_name', '')
                category = act.get('category', '') if isinstance(act, dict) else getattr(act, 'category', '')
                start_str = act.get('time_start', '') if isinstance(act, dict) else getattr(act, 'time_start', '')
                end_str = act.get('time_end', '') if isinstance(act, dict) else getattr(act, 'time_end', '')
                
                start_time = self._parse_time(start_str)
                end_time = self._parse_time(end_str)

                # Rule 2: TIME WINDOW CHECK
                try:
                    if start_time and end_time:
                        start_hour = start_time.hour
                        end_hour = end_time.hour + (end_time.minute / 60.0)
                        
                        if start_hour < 7 or end_hour > 23:
                            violations.append(Violation(
                                rule='time_window_check',
                                severity='critical',
                                details=f"Activity '{name}' outside 07:00-23:00 window.",
                                affected_day=day_num,
                                suggested_fix="Reschedule to normal waking hours."
                            ))
                        elif start_hour < 9 or end_hour > 21:
                            violations.append(Violation(
                                rule='time_window_check',
                                severity='warning',
                                details=f"Activity '{name}' outside preferred 09:00-21:00 window.",
                                affected_day=day_num,
                                suggested_fix="Shift activity closer to mid-day if possible."
                            ))
                except Exception as e:
                    pass

                # Rule 4 prep: Duplicate category count per day
                if category:
                    categories_today[category] = categories_today.get(category, 0) + 1

                # Rule 6: MEAL GAP CHECK
                try:
                    is_meal = category.lower() in ['food', 'restaurant', 'cafe', 'dining', 'meal']
                    if is_meal and end_time:
                        last_meal_time = end_time
                    elif start_time and last_meal_time:
                        gap_hours = (start_time - last_meal_time).total_seconds() / 3600
                        if gap_hours > 5.0:
                            violations.append(Violation(
                                rule='meal_gap_check',
                                severity='info',
                                details=f"Gap of >5 hours without meal before '{name}'.",
                                affected_day=day_num,
                                suggested_fix="Add a food/cafe break."
                            ))
                            last_meal_time = start_time
                except Exception:
                    pass

            # Rule 4 part B: Duplicate categories per day
            try:
                print(f"🔄 Running duplicate_check (categories) for Day {day_num}...")
                for cat, count in categories_today.items():
                    if count > 2:
                        violations.append(Violation(
                            rule='duplicate_check',
                            severity='warning',
                            details=f"More than 2 '{cat}' activities on Day {day_num}.",
                            affected_day=day_num,
                            suggested_fix="Diversify activity categories."
                        ))
            except Exception:
                pass

        # Rule 4 part A: Exact duplicate activities in trip
        try:
            print("🔄 Running duplicate_check (exact names)...")
            seen_names = set()
            for act in all_activities:
                name = act.get('activity_name', '') if isinstance(act, dict) else getattr(act, 'activity_name', '')
                if name:
                    if name in seen_names:
                        violations.append(Violation(
                            rule='duplicate_check',
                            severity='warning',
                            details=f"Activity '{name}' appears multiple times in the trip.",
                            suggested_fix="Replace duplicate activity."
                        ))
                    else:
                        seen_names.add(name)
        except Exception:
            pass

        # Rule 5: REST CHECK
        try:
            print("🛌 Running rest_check...")
            for i in range(len(plan_days) - 1):
                day1 = plan_days[i]
                day2 = plan_days[i+1]
                
                day1_acts = day1.get('activities', []) if isinstance(day1, dict) else getattr(day1, 'activities', [])
                day2_acts = day2.get('activities', []) if isinstance(day2, dict) else getattr(day2, 'activities', [])
                
                if not day1_acts or not day2_acts:
                    continue
                    
                last_act = day1_acts[-1]
                first_act = day2_acts[0]
                
                end_str = last_act.get('time_end', '') if isinstance(last_act, dict) else getattr(last_act, 'time_end', '')
                start_str = first_act.get('time_start', '') if isinstance(first_act, dict) else getattr(first_act, 'time_start', '')
                
                end_time = self._parse_time(end_str)
                start_time = self._parse_time(start_str)
                
                if end_time and start_time:
                    next_day_start = start_time + timedelta(days=1)
                    rest_hours = (next_day_start - end_time).total_seconds() / 3600
                    
                    day1_num = day1.get('day_number', i + 1) if isinstance(day1, dict) else getattr(day1, 'day_number', i + 1)
                    day2_num = day2.get('day_number', i + 2) if isinstance(day2, dict) else getattr(day2, 'day_number', i + 2)
                    
                    if rest_hours < 8.0:
                        violations.append(Violation(
                            rule='rest_check',
                            severity='warning',
                            details=f"Only {rest_hours:.1f}h rest between Day {day1_num} and Day {day2_num}.",
                            suggested_fix="Ensure at least 8 hours between days."
                        ))
        except Exception as e:
            print(f"⚠️ Error in rest_check: {e}")

        # Calculate verdict
        critical_count = sum(1 for v in violations if v.severity == 'critical')
        warning_count = sum(1 for v in violations if v.severity == 'warning')
        info_count = sum(1 for v in violations if v.severity == 'info')
        
        passed = critical_count == 0
        score = max(0.0, 1.0 - (critical_count * 0.3) - (warning_count * 0.1) - (info_count * 0.02))
        
        summary = f"{'PASSED' if passed else 'FAILED'}: {len(violations)} violations ({critical_count} critical, {warning_count} warnings, {info_count} info)"
        print(f"✅ Critic Agent finished: {summary}")
        
        verdict = CriticVerdict(
            passed=passed,
            total_violations=len(violations),
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            violations=violations,
            overall_score=score,
            summary=summary
        )
        
        # Store in planning_state
        try:
            planning_state.evaluation_results = verdict.model_dump()
        except Exception:
            try:
                planning_state['evaluation_results'] = verdict.model_dump()
            except Exception:
                pass
        
        return verdict
