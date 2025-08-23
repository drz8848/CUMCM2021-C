import pandas as pd
import numpy as np
import json

# 读取结果数据
result_df = pd.read_excel('期望供货量预测结果.xlsx')

# 分析结果数据
print("=== 期望供货量分析 ===")

# 1. 按材料分类统计
material_stats = {}
future_weeks = [col for col in result_df.columns if col.startswith('未来第')]

for material in ['A', 'B', 'C']:
    material_data = result_df[result_df['材料分类'] == material]
    weekly_means = [float(material_data[week].mean()) for week in future_weeks]

    material_stats[material] = {
        '供应商数量': int(len(material_data)),
        '平均期望供货量': float(np.mean(weekly_means)),
        '周平均供货量': weekly_means
    }

# 2. 周度趋势分析
weekly_totals = [float(result_df[week].sum()) for week in future_weeks]
weekly_avgs = [float(result_df[week].mean()) for week in future_weeks]

# 3. 供应商供货能力分析
supplier_totals = result_df[future_weeks].sum(axis=1)
supplier_totals_list = [float(x) for x in supplier_totals]

# 4. 供应商分布数据
supplier_ranges = ['0-100', '101-500', '501-1000', '1001-5000', '5000+']
supplier_distribution = [
    int(len(supplier_totals[supplier_totals <= 100])),
    int(len(supplier_totals[(supplier_totals > 100) & (supplier_totals <= 500)])),
    int(len(supplier_totals[(supplier_totals > 500) & (supplier_totals <= 1000)])),
    int(len(supplier_totals[(supplier_totals > 1000) & (supplier_totals <= 5000)])),
    int(len(supplier_totals[supplier_totals > 5000]))
]

# 5. 准备样例数据（前10个供应商的前10周数据）
sample_data = []
for i in range(min(10, len(result_df))):
    row = result_df.iloc[i]
    sample_record = {
        '供应商ID': str(row['供应商ID']),
        '材料分类': str(row['材料分类']),
        '周数据': [float(row[f'未来第{j + 1}周']) for j in range(10)]
    }
    sample_data.append(sample_record)

# 6. 准备可视化数据
viz_data = {
    'sample_data': sample_data,
    'weekly_trend': {
        'weeks': [f'第{i + 1}周' for i in range(24)],
        'total_supply': weekly_totals,
        'avg_supply': weekly_avgs
    },
    'material_comparison': {
        'materials': list(material_stats.keys()),
        'avg_supply': [material_stats[m]['平均期望供货量'] for m in material_stats.keys()],
        'supplier_count': [material_stats[m]['供应商数量'] for m in material_stats.keys()],
        'weekly_trends': {
            m: material_stats[m]['周平均供货量'] for m in material_stats.keys()
        }
    },
    'supplier_distribution': {
        'ranges': supplier_ranges,
        'counts': supplier_distribution
    },
    'summary_stats': {
        'total_suppliers': int(len(result_df)),
        'avg_weekly_supply': float(np.mean(weekly_totals)),
        'max_weekly_supply': float(max(weekly_totals)),
        'min_weekly_supply': float(min(weekly_totals))
    }
}

print("样例数据（前3个供应商）:")
for i, record in enumerate(sample_data[:3]):
    print(f"{i + 1}. {record['供应商ID']} ({record['材料分类']}): {record['周数据'][:5]}...")

print(f"\n周度趋势: 第1周{weekly_totals[0]:.0f}, 第24周{weekly_totals[-1]:.0f}")
print(
    f"材料分类分布: A类{material_stats['A']['供应商数量']}家, B类{material_stats['B']['供应商数量']}家, C类{material_stats['C']['供应商数量']}家")
print(f"供应商分布: {dict(zip(supplier_ranges, supplier_distribution))}")
print(
    f"总体统计: 平均周供货量{viz_data['summary_stats']['avg_weekly_supply']:.0f}, 最高{viz_data['summary_stats']['max_weekly_supply']:.0f}")

print("\n数据准备完成，准备生成HTML报告...")