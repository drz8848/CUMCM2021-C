import pandas as pd
import numpy as np

# 重新读取数据
df = pd.read_excel('附件1.xlsx')

# 提取周数据列
week_columns = [col for col in df.columns if col.startswith('W')]
df_week = df[week_columns].copy()
df_week = df_week.apply(pd.to_numeric, errors='coerce')

# 按24周划分周期（10个周期）
n_periods = 10
period_weeks = 24
total_weeks = n_periods * period_weeks

print(f"周期划分: {n_periods}个周期 × {period_weeks}周 = {total_weeks}周")

# 为每个供应商计算期望供货量
expected_supply = []

for supplier_idx in range(len(df)):
    supplier_id = df.iloc[supplier_idx]['供应商ID']
    material_type = df.iloc[supplier_idx]['材料分类']

    # 获取该供应商的240周数据
    supplier_data = df_week.iloc[supplier_idx].values

    # 按周期分组（10个周期，每个周期24周）
    periods_data = []
    for period in range(n_periods):
        start_idx = period * period_weeks
        end_idx = start_idx + period_weeks
        period_data = supplier_data[start_idx:end_idx]
        periods_data.append(period_data)

    # 计算期望供货量
    weekly_expected = []
    for week_in_period in range(period_weeks):
        # 提取10个周期中对应周次的数据
        week_data = [periods_data[period][week_in_period] for period in range(n_periods)]

        # 移除NaN值
        week_data_clean = [x for x in week_data if pd.notna(x)]

        if not week_data_clean:
            weekly_expected.append(0)
            continue

        # 计算该周次的均值
        week_mean = np.mean(week_data_clean)

        # 筛选条件：供货量/订货量 > 90%（假设订货量=供货量，所以都满足）且 供货量 ≤ 3倍均值
        # 由于假设订货量=供货量，所以供货量/订货量 = 100% > 90%
        valid_data = [x for x in week_data_clean if x <= 3 * week_mean]

        if not valid_data:
            weekly_expected.append(0)
        else:
            # 取最大值作为期望供货量
            weekly_expected.append(max(valid_data))

    # 存储结果
    expected_supply.append({
        '供应商ID': supplier_id,
        '材料分类': material_type,
        **{f'未来第{i + 1}周': weekly_expected[i] for i in range(period_weeks)}
    })

# 创建结果DataFrame
result_df = pd.DataFrame(expected_supply)

print(f"\n期望供货量计算完成，共{len(result_df)}个供应商")
print("\n前5个供应商的期望供货量（前10周）:")
display_cols = ['供应商ID', '材料分类'] + [f'未来第{i + 1}周' for i in range(10)]
print(result_df[display_cols].head())

# 保存结果
result_df.to_excel('期望供货量预测结果.xlsx', index=False)
print(f"\n结果已保存到: 期望供货量预测结果.xlsx")

# 统计信息
print("\n期望供货量统计信息:")
future_weeks = [col for col in result_df.columns if col.startswith('未来第')]
future_data = result_df[future_weeks]
print(f"各周期望供货量平均值:")
for week in future_weeks[:10]:  # 显示前10周
    print(f"{week}: {future_data[week].mean():.2f}")