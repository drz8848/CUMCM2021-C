import pandas as pd
import numpy as np

# 重新加载数据并创建订购方案（之前的代码）
topsis_df = pd.read_excel('供应商TOPSIS评价结果.xlsx')
expected_df = pd.read_excel('期望供货量预测结果.xlsx')
attachment2 = pd.read_excel('附件2.xlsx')

# 计算转运商平均损耗率并排序
week_columns = [col for col in attachment2.columns if col.startswith('W')]
attachment2['平均损耗率'] = attachment2[week_columns].mean(axis=1)
sorted_transporters = attachment2.sort_values('平均损耗率').reset_index(drop=True)
transporter_list = sorted_transporters['转运商ID'].tolist()
print("转运商按损耗率排序:", transporter_list)

# 选择的17家供应商
selected_supplier_ids = ['S229', 'S140', 'S361', 'S201', 'S108', 'S139', 'S151', 'S282', 'S340', 'S275', 'S329', 'S308',
                         'S330', 'S131', 'S395', 'S268', 'S356']
selected_suppliers = topsis_df[topsis_df['供应商ID'].isin(selected_supplier_ids)].copy()
selected_expected = expected_df[expected_df['供应商ID'].isin(selected_supplier_ids)].copy()
supplier_data = pd.merge(selected_suppliers, selected_expected, on=['供应商ID', '材料分类'], how='left')


# 重新创建订购方案
def create_order_plan():
    inventory = {'A': 0, 'B': 0, 'C': 0}
    order_plan = pd.DataFrame(0, index=selected_supplier_ids, columns=[f'第{week:02d}周' for week in range(1, 25)])
    order_plan = order_plan.astype(float)

    cost_coefficients = {'A': 1.2, 'B': 1.1, 'C': 1.0}
    supplier_data_sorted = supplier_data.sort_values(
        by=['材料分类', 'TOPSIS综合得分'],
        ascending=[True, False]
    ).reset_index(drop=True)

    for week in range(1, 25):
        week_col = f'未来第{week}周'
        weekly_production_need = 28200

        equivalent_inventory = sum(inventory[mat] * (1 / material_coefficients[mat]) for mat in ['A', 'B', 'C'])

        if equivalent_inventory < 2 * weekly_production_need:
            needed_equivalent = 2 * weekly_production_need - equivalent_inventory
            remaining_need = needed_equivalent

            for _, supplier in supplier_data_sorted.iterrows():
                if remaining_need <= 0:
                    break

                supplier_id = supplier['供应商ID']
                material = supplier['材料分类']
                expected_supply = supplier[week_col] if pd.notna(supplier[week_col]) else 0

                if expected_supply <= 0:
                    continue

                equivalent_supply = expected_supply * (1 / material_coefficients[material])
                order_amount = min(expected_supply, remaining_need * material_coefficients[material])

                if order_amount > 0:
                    order_plan.loc[supplier_id, f'第{week:02d}周'] = order_amount
                    remaining_need -= order_amount / material_coefficients[material]

        # 更新库存和消耗
        for _, supplier in supplier_data_sorted.iterrows():
            supplier_id = supplier['供应商ID']
            material = supplier['材料分类']
            order_amount = order_plan.loc[supplier_id, f'第{week:02d}周']
            inventory[material] += order_amount

        production_remaining = weekly_production_need
        for material in ['A', 'B', 'C']:
            if production_remaining <= 0:
                break

            material_needed = production_remaining * material_coefficients[material]
            actual_consumption = min(inventory[material], material_needed)

            if actual_consumption > 0:
                inventory[material] -= actual_consumption
                production_remaining -= actual_consumption / material_coefficients[material]

    return order_plan


# 创建订购方案
order_plan = create_order_plan()


# 制定转运方案
def create_transport_plan(order_plan):
    transport_capacity = 6000  # 每家转运商每周最大运输能力
    transport_plan = pd.DataFrame(index=selected_supplier_ids)

    # 为每个供应商分配首选转运商（基于供应商排名和转运商损耗率）
    supplier_rank = {supplier_id: i for i, supplier_id in enumerate(selected_supplier_ids)}
    preferred_transporters = {}

    for i, supplier_id in enumerate(selected_supplier_ids):
        preferred_transporters[supplier_id] = transporter_list[i % len(transporter_list)]

    # 每周转运计划
    for week in range(1, 25):
        week_col = f'第{week:02d}周'
        transport_plan[week_col] = ''

        # 本周需要运输的货物
        weekly_orders = order_plan[week_col].copy()
        weekly_orders = weekly_orders[weekly_orders > 0].sort_values(ascending=False)

        if weekly_orders.empty:
            continue

        # 初始化转运商使用量
        transporter_usage = {transporter: 0 for transporter in transporter_list}

        # 为每个供应商分配转运商
        for supplier_id, amount in weekly_orders.items():
            if amount <= 0:
                continue

            # 尝试使用首选转运商
            preferred_t = preferred_transporters[supplier_id]

            if transporter_usage[preferred_t] + amount <= transport_capacity:
                transport_plan.loc[supplier_id, week_col] = preferred_t
                transporter_usage[preferred_t] += amount
            else:
                # 首选转运商容量不足，寻找其他可用转运商
                for t in transporter_list:
                    if transporter_usage[t] + amount <= transport_capacity:
                        transport_plan.loc[supplier_id, week_col] = t
                        transporter_usage[t] += amount
                        break
                else:
                    # 如果所有转运商都满了，需要拆分运输
                    remaining = amount
                    for t in transporter_list:
                        available = transport_capacity - transporter_usage[t]
                        if available > 0:
                            use_amount = min(available, remaining)
                            transport_plan.loc[supplier_id, week_col] += f",{t}({use_amount:.0f})"
                            transporter_usage[t] += use_amount
                            remaining -= use_amount
                            if remaining <= 0:
                                break

    return transport_plan


# 创建转运方案
transport_plan = create_transport_plan(order_plan)

print("转运方案前5周示例:")
print(transport_plan[['第01周', '第02周', '第03周', '第04周', '第05周']].head(10))

# 分析转运方案效果
print(f"\n转运方案分析:")
for week in range(1, 25):
    week_col = f'第{week:02d}周'
    weekly_transport = transport_plan[week_col].value_counts()
    print(f"\n{week_col} 转运商使用情况:")
    for transporter, count in weekly_transport.items():
        if pd.notna(transporter) and transporter != '':
            print(f"  {transporter}: {count}家供应商")
