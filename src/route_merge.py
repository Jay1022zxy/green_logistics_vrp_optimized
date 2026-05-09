from task_eval import evaluate_task_route


def merge_routes_once(routes, problem_data, task_map, use_policy=False):
    n = len(routes)

    for i in range(n):
        for j in range(i + 1, n):
            route_i = routes[i]
            route_j = routes[j]

            # 先只尝试同车型合并
            if route_i["vehicle_type"].name != route_j["vehicle_type"].name:
                continue

            old_eval_i = evaluate_task_route(
                route=route_i["nodes"],
                vehicle_type=route_i["vehicle_type"],
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy
            )
            old_eval_j = evaluate_task_route(
                route=route_j["nodes"],
                vehicle_type=route_j["vehicle_type"],
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy
            )

            old_cost = old_eval_i["total_cost"] + old_eval_j["total_cost"]

            merged_nodes = route_i["nodes"][:-1] + route_j["nodes"][1:]

            new_eval = evaluate_task_route(
                route=merged_nodes,
                vehicle_type=route_i["vehicle_type"],
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy
            )

            if new_eval["feasible"] and new_eval["total_cost"] < old_cost:
                new_routes = routes[:i] + routes[i + 1:j] + routes[j + 1:]
                new_routes.insert(i, {
                    "vehicle_type": route_i["vehicle_type"],
                    "nodes": merged_nodes
                })
                return new_routes, True

    return routes, False


def merge_routes_iteratively(routes, problem_data, task_map, use_policy=False, max_rounds=50):
    current_routes = routes.copy()

    for _ in range(max_rounds):
        current_routes, improved = merge_routes_once(
            current_routes, problem_data, task_map, use_policy
        )
        if not improved:
            break

    return current_routes