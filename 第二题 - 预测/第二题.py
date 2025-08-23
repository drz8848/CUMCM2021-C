import pandas as pd
import numpy as np
import random
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# 设置随机种子以确保结果可复现
np.random.seed(42)
random.seed(42)


# ----------------------------
# 1. 数据准备
# ----------------------------
def load_data():
    """加载所有必要的数据"""
    print("加载数据...")

    # 供应商数据
    df_supply = pd.read_excel('附件1.xlsx', sheet_name='供应商的供货量（m³）')
    df_topsis = pd.read_excel('供应商TOPSIS评价结果.xlsx')

    # 合并供应商数据
    df_suppliers = pd.merge(
        df_supply[['供应商ID', '材料分类']],
        df_topsis[['供应商ID', '材料分类', 'TOPSIS综合得分', '排名', '平均供货强度', '到货率', '供货持续性']],
        on=['供应商ID', '材料分类']
    )

    # 转运商数据
    df_transport = pd.read_excel('附件2.xlsx', sheet_name='运输损耗率（%）')

    return df_suppliers, df_transport


# ----------------------------
# 2. 问题参数设置
# ----------------------------
def setup_parameters():
    """设置问题的关键参数"""
    params = {
        # 企业生产参数
        'weekly_capacity': 28200,  # 每周产能（立方米）
        'planning_weeks': 24,  # 计划周期（周）
        'safety_stock_weeks': 2,  # 安全库存（周）

        # 原材料参数
        'material_coefficients': {  # 单位产品原材料消耗系数
            'A': 0.6,
            'B': 0.66,
            'C': 0.72
        },
        'cost_coefficients': {  # 相对成本系数（C类为基准）
            'A': 1.2,
            'B': 1.1,
            'C': 1.0
        },

        # 转运商参数
        'transport_capacity': 6000,  # 每家转运商周运输能力（立方米）

        # 遗传算法参数
        'population_size': 50,
        'generations': 100,
        'mutation_rate': 0.1,
        'crossover_rate': 0.8,

        # 供应商选择参数
        'suppliers_per_material': {  # 每类原材料选择的供应商数量
            'A': 8,
            'B': 8,
            'C': 8
        }
    }

    # 计算需求参数
    params['material_demand'] = {
        material: params['weekly_capacity'] * coef
        for material, coef in params['material_coefficients'].items()
    }

    params['safety_stock'] = {
        material: params['safety_stock_weeks'] * demand
        for material, demand in params['material_demand'].items()
    }

    return params


# ----------------------------
# 3. 供应商选择
# ----------------------------
def select_suppliers(df_suppliers, params):
    """选择高质量的供应商"""
    print("选择供应商...")

    selected_suppliers = {}

    for material_type in ['A', 'B', 'C']:
        # 筛选该类别的供应商
        type_suppliers = df_suppliers[df_suppliers['材料分类'] == material_type].copy()

        # 按综合得分排序
        type_suppliers = type_suppliers.sort_values('TOPSIS综合得分', ascending=False)

        # 选择前N名供应商
        num_suppliers = params['suppliers_per_material'][material_type]
        selected = type_suppliers.head(num_suppliers).copy()

        # 计算权重（基于综合得分）
        total_score = selected['TOPSIS综合得分'].sum()
        selected['weight'] = selected['TOPSIS综合得分'] / total_score

        selected_suppliers[material_type] = selected

        print(f"{material_type}类原材料: 选择{len(selected)}家供应商")

    return selected_suppliers


# ----------------------------
# 4. 转运商分析
# ----------------------------
def analyze_transporters(df_transport, params):
    """分析转运商的损耗率和能力"""
    print("分析转运商...")

    transporters = []

    for _, row in df_transport.iterrows():
        # 计算前24周的平均损耗率
        loss_rates = row.iloc[1:25].values  # 前24周数据
        avg_loss = np.mean(loss_rates)

        transporters.append({
            'id': row['转运商ID'],
            'avg_loss_rate': avg_loss,
            'capacity': params['transport_capacity']
        })

    # 按损耗率排序
    transporters = sorted(transporters, key=lambda x: x['avg_loss_rate'])

    print(f"转运商损耗率排序:")
    for i, transporter in enumerate(transporters):
        print(f"  {i + 1}. {transporter['id']}: {transporter['avg_loss_rate']:.2f}%")

    return transporters


# ----------------------------
# 5. 遗传算法实现
# ----------------------------
class GeneticAlgorithm:
    def __init__(self, selected_suppliers, transporters, params):
        self.selected_suppliers = selected_suppliers
        self.transporters = transporters
        self.params = params

        # 准备数据结构
        self.all_suppliers = []
        for material_type, suppliers in selected_suppliers.items():
            for _, supplier in suppliers.iterrows():
                self.all_suppliers.append({
                    'id': supplier['供应商ID'],
                    'material': material_type,
                    'avg_supply': supplier['平均供货强度'],
                    'score': supplier['TOPSIS综合得分'],
                    'weight': supplier['weight']
                })

        self.num_suppliers = len(self.all_suppliers)
        self.num_transporters = len(transporters)
        self.num_weeks = params['planning_weeks']

        print(f"\n遗传算法初始化:")
        print(f"  供应商数量: {self.num_suppliers}")
        print(f"  转运商数量: {self.num_transporters}")
        print(f"  计划周期: {self.num_weeks}周")

    def initialize_population(self):
        """初始化种群"""
        population = []

        for _ in range(self.params['population_size']):
            # 染色体结构: [供应商1周1订货量, 供应商1周1转运商, ..., 供应商N周24转运商]
            chromosome = []

            for supplier in self.all_suppliers:
                for week in range(self.num_weeks):
                    # 订货量: 基于平均供货量的随机值
                    order_qty = max(0, supplier['avg_supply'] * np.random.uniform(0.8, 1.2))

                    # 转运商分配: 优先选择损耗率低的
                    transporter_idx = np.random.choice(
                        range(self.num_transporters),
                        p=[0.7, 0.15, 0.05, 0.03, 0.02, 0.02, 0.02, 0.01]  # 优先选择前几个转运商
                    )

                    chromosome.extend([order_qty, transporter_idx])

            population.append(chromosome)

        return population

    def decode_chromosome(self, chromosome):
        """解码染色体为可读的方案"""
        decoded = []
        idx = 0

        for supplier in self.all_suppliers:
            supplier_plan = {
                'id': supplier['id'],
                'material': supplier['material'],
                'weeks': []
            }

            for week in range(self.num_weeks):
                order_qty = chromosome[idx]
                transporter_idx = int(chromosome[idx + 1])

                supplier_plan['weeks'].append({
                    'week': week + 1,
                    'order_qty': order_qty,
                    'transporter': self.transporters[transporter_idx]['id'],
                    'transporter_idx': transporter_idx,
                    'loss_rate': self.transporters[transporter_idx]['avg_loss_rate']
                })

                idx += 2

            decoded.append(supplier_plan)

        return decoded

    def calculate_fitness(self, chromosome):
        """计算染色体的适应度"""
        decoded = self.decode_chromosome(chromosome)

        # 初始化库存
        inventory = {'A': 0, 'B': 0, 'C': 0}

        # 初始化每周转运商使用量
        transporter_usage = {t['id']: [0 for _ in range(self.num_weeks)] for t in self.transporters}

        total_cost = 0
        total_loss = 0
        stockout_penalty = 0
        transport_penalty = 0

        # 模拟24周的运营
        for week in range(self.num_weeks):
            # 本周各类原材料的总订货量和接收量
            weekly_order = {'A': 0, 'B': 0, 'C': 0}
            weekly_receive = {'A': 0, 'B': 0, 'C': 0}

            # 处理每个供应商的订单
            for supplier_plan in decoded:
                week_data = supplier_plan['weeks'][week]
                material = supplier_plan['material']
                transporter_id = week_data['transporter']

                # 实际供货量（考虑到货率）
                supplier_idx = next(i for i, s in enumerate(self.all_suppliers) if s['id'] == supplier_plan['id'])
                actual_supply = week_data['order_qty'] * self.selected_suppliers[material].iloc[
                    supplier_idx % len(self.selected_suppliers[material])]['到货率']

                # 运输损耗
                loss_rate = week_data['loss_rate'] / 100
                receive_qty = actual_supply * (1 - loss_rate)

                # 更新统计
                weekly_order[material] += week_data['order_qty']
                weekly_receive[material] += receive_qty
                total_loss += actual_supply * loss_rate

                # 更新转运商使用量
                transporter_usage[transporter_id][week] += actual_supply

                # 原材料成本（基于相对成本）
                total_cost += week_data['order_qty'] * self.params['cost_coefficients'][material]

            # 更新库存
            for material in ['A', 'B', 'C']:
                inventory[material] += weekly_receive[material]

            # 计算本周生产所需原材料
            production_demand = {}
            total_effective_demand = 0

            # 优先使用低成本原材料
            for material in ['C', 'B', 'A']:  # 注意顺序：C类优先
                max_possible = inventory[material] / self.params['material_coefficients'][material]
                production_demand[material] = min(max_possible, self.params['weekly_capacity'] - total_effective_demand)
                total_effective_demand += production_demand[material]

            # 消耗原材料
            for material in ['A', 'B', 'C']:
                consumption = production_demand[material] * self.params['material_coefficients'][material]
                inventory[material] -= consumption

            # 检查安全库存
            for material in ['A', 'B', 'C']:
                if inventory[material] < self.params['safety_stock'][material]:
                    stockout_penalty += (self.params['safety_stock'][material] - inventory[material]) * 10  # 高惩罚

            # 检查转运商能力约束
            for transporter_id, usage in transporter_usage.items():
                if usage[week] > self.params['transport_capacity']:
                    transport_penalty += (usage[week] - self.params['transport_capacity']) * 5  # 中等惩罚

        # 最终适应度计算
        # 目标：最小化成本 + 损耗 + 惩罚
        fitness = total_cost + total_loss * 10 + stockout_penalty + transport_penalty

        return fitness, {
            'total_cost': total_cost,
            'total_loss': total_loss,
            'stockout_penalty': stockout_penalty,
            'transport_penalty': transport_penalty,
            'final_inventory': inventory.copy()
        }

    def select_parents(self, population, fitness_scores):
        """选择父母（轮盘赌选择）"""
        # 使用适应度的倒数作为概率（因为我们要最小化适应度）
        total_fitness = sum(1 / score for score in fitness_scores)
        probabilities = [1 / score / total_fitness for score in fitness_scores]

        parents = random.choices(population, weights=probabilities, k=2)
        return parents[0], parents[1]

    def crossover(self, parent1, parent2):
        """单点交叉"""
        if random.random() > self.params['crossover_rate']:
            return parent1.copy(), parent2.copy()

        point = random.randint(1, len(parent1) - 1)
        child1 = parent1[:point] + parent2[point:]
        child2 = parent2[:point] + parent1[point:]

        return child1, child2

    def mutate(self, chromosome):
        """变异操作"""
        mutated = chromosome.copy()

        for i in range(len(mutated)):
            if random.random() < self.params['mutation_rate']:
                if i % 2 == 0:  # 订货量
                    supplier_idx = (i // 2) // self.num_weeks
                    supplier = self.all_suppliers[supplier_idx]
                    mutated[i] = max(0, supplier['avg_supply'] * np.random.uniform(0.7, 1.3))
                else:  # 转运商
                    mutated[i] = random.randint(0, self.num_transporters - 1)

        return mutated

    def run(self):
        """运行遗传算法"""
        print("\n开始遗传算法优化...")

        # 初始化种群
        population = self.initialize_population()
        best_fitness = float('inf')
        best_solution = None
        best_stats = None

        # 记录进化过程
        evolution_history = []

        for generation in range(self.params['generations']):
            # 计算适应度
            fitness_scores = []
            stats_list = []

            for chromosome in population:
                fitness, stats = self.calculate_fitness(chromosome)
                fitness_scores.append(fitness)
                stats_list.append(stats)

            # 找到当前代的最佳解
            current_best_idx = np.argmin(fitness_scores)
            current_best_fitness = fitness_scores[current_best_idx]
            current_best_solution = population[current_best_idx]
            current_best_stats = stats_list[current_best_idx]

            # 更新全局最佳解
            if current_best_fitness < best_fitness:
                best_fitness = current_best_fitness
                best_solution = current_best_solution
                best_stats = current_best_stats

            # 记录进化历史
            evolution_history.append({
                'generation': generation + 1,
                'best_fitness': best_fitness,
                'avg_fitness': np.mean(fitness_scores),
                'current_best_fitness': current_best_fitness
            })

            # 打印进度
            if (generation + 1) % 10 == 0 or generation == 0:
                print(
                    f"第{generation + 1}代: 最佳适应度 = {best_fitness:.2f}, 平均适应度 = {np.mean(fitness_scores):.2f}")

            # 创建新一代
            new_population = [best_solution]  # 保留精英解

            while len(new_population) < self.params['population_size']:
                # 选择父母
                parent1, parent2 = self.select_parents(population, fitness_scores)

                # 交叉
                child1, child2 = self.crossover(parent1, parent2)

                # 变异
                child1 = self.mutate(child1)
                child2 = self.mutate(child2)

                new_population.extend([child1, child2])

            # 截断到种群大小
            population = new_population[:self.params['population_size']]

        print(f"\n优化完成!")
        print(f"最佳适应度: {best_fitness:.2f}")
        print(f"总成本: {best_stats['total_cost']:.2f}")
        print(f"总损耗: {best_stats['total_loss']:.2f} 立方米")
        print(f"最终库存: {best_stats['final_inventory']}")

        return best_solution, best_stats, evolution_history


# ----------------------------
# 6. 结果分析和可视化
# ----------------------------
def analyze_results(best_solution, ga, best_stats):
    """分析优化结果"""
    print("\n分析优化结果...")

    # 解码最佳方案
    decoded_solution = ga.decode_chromosome(best_solution)

    # 计算每周各类原材料的订货量和接收量
    weekly_summary = []

    for week in range(ga.num_weeks):
        week_data = {
            'week': week + 1,
            'order_A': 0, 'order_B': 0, 'order_C': 0,
            'receive_A': 0, 'receive_B': 0, 'receive_C': 0,
            'transporter_usage': {}
        }

        # 初始化转运商使用量
        for transporter in ga.transporters:
            week_data['transporter_usage'][transporter['id']] = 0

        # 汇总每个供应商的数据
        for supplier_plan in decoded_solution:
            material = supplier_plan['material']
            week_plan = supplier_plan['weeks'][week]

            # 实际供货量
            supplier_idx = next(i for i, s in enumerate(ga.all_suppliers) if s['id'] == supplier_plan['id'])
            actual_supply = week_plan['order_qty'] * \
                            ga.selected_suppliers[material].iloc[supplier_idx % len(ga.selected_suppliers[material])][
                                '到货率']

            # 接收量（考虑损耗）
            receive_qty = actual_supply * (1 - week_plan['loss_rate'] / 100)

            # 更新周数据
            week_data[f'order_{material}'] += week_plan['order_qty']
            week_data[f'receive_{material}'] += receive_qty
            week_data['transporter_usage'][week_plan['transporter']] += actual_supply

        weekly_summary.append(week_data)

    # 计算总体统计
    total_orders = {
        'A': sum(wd['order_A'] for wd in weekly_summary),
        'B': sum(wd['order_B'] for wd in weekly_summary),
        'C': sum(wd['order_C'] for wd in weekly_summary)
    }

    total_receive = {
        'A': sum(wd['receive_A'] for wd in weekly_summary),
        'B': sum(wd['receive_B'] for wd in weekly_summary),
        'C': sum(wd['receive_C'] for wd in weekly_summary)
    }

    print(f"\n=== 总体统计 ===")
    print(f"总订货量:")
    for material in ['A', 'B', 'C']:
        print(f"  {material}类: {total_orders[material]:.0f} 立方米")

    print(f"\n总接收量:")
    for material in ['A', 'B', 'C']:
        print(f"  {material}类: {total_receive[material]:.0f} 立方米")

    print(f"\n总损耗: {sum(total_orders.values()) - sum(total_receive.values()):.0f} 立方米")
    print(
        f"平均损耗率: {(sum(total_orders.values()) - sum(total_receive.values())) / sum(total_orders.values()) * 100:.2f}%")

    # 转运商使用统计
    print(f"\n转运商使用统计:")
    for transporter in ga.transporters:
        total_usage = sum(wd['transporter_usage'][transporter['id']] for wd in weekly_summary)
        avg_weekly = total_usage / ga.num_weeks
        capacity_usage = avg_weekly / ga.params['transport_capacity'] * 100
        print(
            f"  {transporter['id']}: 总运输 {total_usage:.0f} 立方米, 平均每周 {avg_weekly:.0f} 立方米, 能力利用率 {capacity_usage:.1f}%")

    return decoded_solution, weekly_summary


# ----------------------------
# 7. 填充结果到Excel文件
# ----------------------------
def fill_excel_files(decoded_solution, weekly_summary, ga):
    """将结果填充到附件A和附件B"""
    print("\n填充Excel文件...")

    # ----------------------------
    # 填充附件A: 订购方案
    # ----------------------------
    try:
        # 读取附件A
        df_A = pd.read_excel('附件A.xlsx', sheet_name='问题2的订购方案结果')

        # 创建结果DataFrame
        order_results = []

        # 获取所有供应商ID
        all_supplier_ids = [s['id'] for s in ga.all_suppliers]

        for supplier_id in all_supplier_ids:
            supplier_row = {'供应商ID': supplier_id}

            # 找到该供应商的计划
            supplier_plan = next((sp for sp in decoded_solution if sp['id'] == supplier_id), None)

            if supplier_plan:
                for week in range(ga.num_weeks):
                    week_data = supplier_plan['weeks'][week]
                    supplier_row[f'第{week + 1:02d}周'] = week_data['order_qty']
            else:
                # 如果没有找到供应商计划，填充0
                for week in range(ga.num_weeks):
                    supplier_row[f'第{week + 1:02d}周'] = 0

            order_results.append(supplier_row)

        # 找到数据开始的行（跳过前5行说明）
        data_start_row = 5

        # 填充数据
        for i, supplier_row in enumerate(order_results):
            row_idx = data_start_row + i
            if row_idx >= len(df_A):
                # 如果行数不够，添加新行
                df_A.loc[row_idx] = [np.nan] * len(df_A.columns)

            # 填充供应商ID
            df_A.iloc[row_idx, 0] = supplier_row['供应商ID']

            # 填充每周订货量
            for week in range(ga.num_weeks):
                col_idx = week + 1
                if col_idx < len(df_A.columns):
                    df_A.iloc[row_idx, col_idx] = supplier_row[f'第{week + 1:02d}周']

        # 保存到附件A
        with pd.ExcelWriter('../附件A.xlsx', engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_A.to_excel(writer, sheet_name='问题2的订购方案结果', index=False)

        print("附件A填充完成!")

    except Exception as e:
        print(f"填充附件A时出错: {e}")

    # ----------------------------
    # 填充附件B: 转运方案
    # ----------------------------
    try:
        # 读取附件B
        df_B = pd.read_excel('附件B.xlsx', sheet_name='问题2的转运方案结果')

        # 创建结果DataFrame
        transport_results = []

        for supplier_id in all_supplier_ids:
            supplier_row = {'供应商ID': supplier_id}

            # 找到该供应商的计划
            supplier_plan = next((sp for sp in decoded_solution if sp['id'] == supplier_id), None)

            if supplier_plan:
                for week in range(ga.num_weeks):
                    week_data = supplier_plan['weeks'][week]
                    supplier_row[f'第{week + 1:02d}周'] = week_data['transporter']
            else:
                # 如果没有找到供应商计划，填充空
                for week in range(ga.num_weeks):
                    supplier_row[f'第{week + 1:02d}周'] = ''

            transport_results.append(supplier_row)

        # 找到数据开始的行（跳过前5行说明）
        data_start_row = 5

        # 填充数据
        for i, supplier_row in enumerate(transport_results):
            row_idx = data_start_row + i
            if row_idx >= len(df_B):
                # 如果行数不够，添加新行
                df_B.loc[row_idx] = [np.nan] * len(df_B.columns)

            # 填充供应商ID
            df_B.iloc[row_idx, 0] = supplier_row['供应商ID']

            # 填充每周转运商
            for week in range(ga.num_weeks):
                col_idx = week + 1
                if col_idx < len(df_B.columns):
                    df_B.iloc[row_idx, col_idx] = supplier_row[f'第{week + 1:02d}周']

        # 保存到附件B
        with pd.ExcelWriter('../附件B.xlsx', engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_B.to_excel(writer, sheet_name='问题2的转运方案结果', index=False)

        print("附件B填充完成!")

    except Exception as e:
        print(f"填充附件B时出错: {e}")

    return True


# ----------------------------
# 8. 生成可视化HTML报告
# ----------------------------
def generate_html_report(decoded_solution, weekly_summary, ga, best_stats, evolution_history):
    """生成可视化HTML报告"""
    print("\n生成HTML报告...")

    # 准备样例数据
    sample_suppliers = decoded_solution[:10]  # 前10个供应商
    sample_weeks = weekly_summary[:10]  # 前10周数据

    # 转换为JavaScript可用的格式
    import json

    # 供应商样例数据
    supplier_data = []
    for supplier in sample_suppliers:
        supplier_info = {
            'id': supplier['id'],
            'material': supplier['material'],
            'weekly_orders': [week['order_qty'] for week in supplier['weeks'][:10]],
            'transporters': [week['transporter'] for week in supplier['weeks'][:10]]
        }
        supplier_data.append(supplier_info)

    # 周数据样例
    week_data = []
    for week in sample_weeks:
        week_info = {
            'week': week['week'],
            'order_A': week['order_A'],
            'order_B': week['order_B'],
            'order_C': week['order_C'],
            'receive_A': week['receive_A'],
            'receive_B': week['receive_B'],
            'receive_C': week['receive_C']
        }
        week_data.append(week_info)

    # 进化历史数据
    evolution_data = []
    for gen in evolution_history[::5]:  # 每5代取一个点
        evolution_data.append({
            'generation': gen['generation'],
            'best_fitness': gen['best_fitness'],
            'avg_fitness': gen['avg_fitness']
        })

    # 转运商使用数据
    transporter_usage = {}
    for transporter in ga.transporters:
        total_usage = sum(wd['transporter_usage'][transporter['id']] for wd in weekly_summary)
        transporter_usage[transporter['id']] = {
            'total': total_usage,
            'avg_weekly': total_usage / ga.num_weeks,
            'loss_rate': transporter['avg_loss_rate']
        }

    # 原材料成本分析
    material_costs = {
        'A': sum(wd['order_A'] for wd in weekly_summary) * ga.params['cost_coefficients']['A'],
        'B': sum(wd['order_B'] for wd in weekly_summary) * ga.params['cost_coefficients']['B'],
        'C': sum(wd['order_C'] for wd in weekly_summary) * ga.params['cost_coefficients']['C']
    }

