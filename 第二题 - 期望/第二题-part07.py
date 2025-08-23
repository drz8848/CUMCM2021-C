import pandas as pd
import numpy as np
import random
from scipy.optimize import minimize
import os
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# 设置中文显示
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]


class SupplyChainOptimizer:
    def __init__(self, data_paths):
        """初始化优化器，加载所有必要数据"""
        self.data_paths = data_paths
        self.load_data()
        self.initialize_parameters()

    def load_data(self):
        """加载所有输入数据"""
        # 加载供应商TOPSIS评价结果
        self.topsis_results = pd.read_excel(
            self.data_paths['topsis_results'],
            sheet_name=None
        )

        # 加载历史供应商数据
        self.supplier_data = pd.read_excel(
            self.data_paths['supplier_data'],
            sheet_name=None
        )

        # 加载转运商数据
        self.transporter_data = pd.read_excel(
            self.data_paths['transporter_data']
        )

        # 加载期望供货量预测结果
        self.demand_forecast = pd.read_excel(
            self.data_paths['demand_forecast']
        )

        # 加载附件A和B模板
        self.template_a = pd.read_excel(
            self.data_paths['template_a'],
            sheet_name=None,
            header=None
        )
        self.template_b = pd.read_excel(
            self.data_paths['template_b'],
            sheet_name=None,
            header=None
        )

    def initialize_parameters(self):
        """初始化模型参数"""
        # 生产参数
        self.weekly_capacity = 28200  # 每周产能(立方米)
        self.weeks = 24  # 计划周期
        self.production_weeks_per_year = 48  # 每年生产周数

        # 原材料转换系数
        self.material_conversion = {
            'A': 1 / 0.6,  # A类材料产能系数
            'B': 1 / 0.66,  # B类材料产能系数
            'C': 1 / 0.72  # C类材料产能系数
        }

        # 原材料成本系数 (以C类为基准)
        self.cost_coefficients = {
            'A': 1.2,  # A类比C类高20%
            'B': 1.1,  # B类比C类高10%
            'C': 1.0  # C类基准
        }

        # 库存参数
        self.min_inventory_weeks = 2  # 最少库存周数
        self.min_inventory = self.weekly_capacity * self.min_inventory_weeks  # 最少库存量

        # 转运参数
        self.transporter_capacity = 6000  # 转运商每周运输能力(立方米)

        # 遗传算法参数
        self.ga_params = {
            'population_size': 50,
            'generations': 100,
            'mutation_rate': 0.1,
            'crossover_rate': 0.8
        }

    def select_suppliers(self):
        """
        多目标规划选择供应商：
        1. 最小化供应商数量
        2. 最大化TOPSIS评分总和
        """
        # 假设从TOPSIS结果中提取供应商评分
        topsis_scores = []
        for sheet in self.topsis_results:
            df = self.topsis_results[sheet]
            # 假设第一列是供应商ID，最后一列是TOPSIS评分
            if len(df.columns) >= 2:
                for _, row in df.iterrows():
                    supplier_id = row[0]
                    score = row.iloc[-1]
                    topsis_scores.append((supplier_id, score, sheet))

        # 按评分降序排序
        topsis_scores.sort(key=lambda x: x[1], reverse=True)

        # 计算总需求(等效材料)
        total_demand = self.calculate_total_demand()

        # 累计供应商产能，直到满足总需求
        selected_suppliers = []
        cumulative_capacity = 0

        for supplier in topsis_scores:
            supplier_id, score, material_type = supplier
            # 估算供应商产能(这里使用历史数据的平均值)
            capacity = self.estimate_supplier_capacity(supplier_id, material_type)

            selected_suppliers.append({
                'id': supplier_id,
                'score': score,
                'material_type': material_type,
                'capacity': capacity
            })

            cumulative_capacity += capacity * self.material_conversion[material_type]

            # 当累计产能超过总需求的1.2倍时停止(考虑不确定性)
            if cumulative_capacity >= total_demand * 1.2:
                break

        self.selected_suppliers = selected_suppliers
        print(f"选择的供应商数量: {len(selected_suppliers)}")
        print(f"总等效产能: {cumulative_capacity:.2f}")
        print(f"总需求: {total_demand:.2f}")

        return selected_suppliers

    def calculate_total_demand(self):
        """计算24周的总等效材料需求"""
        # 每周产能对应的等效材料需求
        weekly_equivalent_demand = self.weekly_capacity

        # 24周总需求
        total_demand = weekly_equivalent_demand * self.weeks
        return total_demand

    def estimate_supplier_capacity(self, supplier_id, material_type):
        """根据历史数据估算供应商产能"""
        # 在实际应用中，这里应该根据历史数据计算供应商的平均供货能力
        # 这里简化处理，假设从供应商数据中查找
        for sheet in self.supplier_data:
            df = self.supplier_data[sheet]
            if supplier_id in df.values:
                # 找到该供应商的历史数据
                supplier_rows = df[df.iloc[:, 0] == supplier_id]
                if not supplier_rows.empty:
                    # 计算平均周供货量
                    supply_columns = [col for col in df.columns if '供货量' in str(col)]
                    if supply_columns:
                        avg_supply = supplier_rows[supply_columns].mean().mean()
                        return avg_supply
        # 如果找不到，返回一个默认值
        return 1000

    def optimize_order_plan(self):
        """优化24周的订购计划"""
        # 初始化库存
        current_inventory = self.min_inventory  # 初始库存满足两周需求
        order_plan = []

        # 按周优化
        for week in range(1, self.weeks + 1):
            # 获取本周需求预测
            week_demand = self.get_weekly_demand(week)

            # 应用遗传算法优化本周订购计划
            weekly_orders = self.genetic_algorithm_optimize_orders(
                week, current_inventory, week_demand
            )

            order_plan.append({
                'week': week,
                'orders': weekly_orders,
                'starting_inventory': current_inventory,
                'demand': week_demand
            })

            # 计算本周结束时的库存
            total_supply = sum(
                order['quantity'] * self.material_conversion[order['material_type']]
                for order in weekly_orders
            )
            current_inventory = max(
                self.min_inventory,
                current_inventory + total_supply - week_demand
            )

        self.order_plan = order_plan
        return order_plan

    def get_weekly_demand(self, week):
        """获取指定周的需求"""
        # 从预测结果中获取，或根据产能计算
        if week <= len(self.demand_forecast):
            # 假设第一列是周数，第二列是需求
            return self.demand_forecast.iloc[week - 1, 1]
        else:
            # 如果没有预测数据，使用平均需求
            return self.weekly_capacity

    def genetic_algorithm_optimize_orders(self, week, current_inventory, week_demand):
        """使用遗传算法优化单周订购计划"""
        # 问题：在满足需求和库存约束的前提下，最小化采购成本

        # 初始化种群
        population = self.initialize_population()

        for generation in range(self.ga_params['generations']):
            # 评估适应度
            fitness = [self.evaluate_fitness(individual, week_demand, current_inventory)
                       for individual in population]

            # 选择
            selected = self.selection(population, fitness)

            # 交叉
            offspring = self.crossover(selected)

            # 变异
            offspring = self.mutate(offspring)

            # 替换种群
            population = offspring

        # 找到最优个体
        best_idx = np.argmax([self.evaluate_fitness(ind, week_demand, current_inventory)
                              for ind in population])
        best_individual = population[best_idx]

        # 转换为订购计划格式
        weekly_orders = []
        for i, supplier in enumerate(self.selected_suppliers):
            if best_individual[i] > 0:
                weekly_orders.append({
                    'supplier_id': supplier['id'],
                    'material_type': supplier['material_type'],
                    'quantity': best_individual[i]
                })

        return weekly_orders

    def initialize_population(self):
        """初始化遗传算法种群"""
        population = []
        num_suppliers = len(self.selected_suppliers)

        for _ in range(self.ga_params['population_size']):
            # 为每个供应商生成随机订购量
            individual = []
            for supplier in self.selected_suppliers:
                # 基于供应商产能的随机订购量
                max_qty = supplier['capacity'] * 1.2  # 最多不超过产能的1.2倍
                min_qty = 0
                qty = random.uniform(min_qty, max_qty)
                individual.append(qty if random.random() > 0.7 else 0)  # 30%概率不订购
            population.append(individual)

        return population

    def evaluate_fitness(self, individual, demand, current_inventory):
        """评估个体适应度"""
        # 计算总成本
        total_cost = 0
        total_supply = 0

        for i, qty in enumerate(individual):
            if qty <= 0:
                continue

            supplier = self.selected_suppliers[i]
            material_type = supplier['material_type']

            # 计算成本 (基于C类的相对成本)
            total_cost += qty * self.cost_coefficients[material_type]

            # 计算等效供应量
            total_supply += qty * self.material_conversion[material_type]

        # 计算库存变化
        final_inventory = current_inventory + total_supply - demand

        # 惩罚库存不足
        if final_inventory < self.min_inventory:
            return 0  # 不可行解

        # 适应度是成本的倒数(最小化成本)加上库存合理性奖励
        inventory_ratio = final_inventory / (self.min_inventory * 2)  # 理想库存是最小库存的2倍
        inventory_reward = 1.0 - abs(1.0 - inventory_ratio)

        return (1.0 / (total_cost + 1e-6)) * (1.0 + inventory_reward)

    def selection(self, population, fitness):
        """选择操作"""
        # 轮盘赌选择
        total_fitness = sum(fitness)
        probabilities = [f / total_fitness for f in fitness]

        selected = []
        for _ in range(len(population)):
            # 随机选择一个个体
            selected_idx = np.random.choice(len(population), p=probabilities)
            selected.append(population[selected_idx])

        return selected

    def crossover(self, population):
        """交叉操作"""
        offspring = []

        for i in range(0, len(population), 2):
            parent1 = population[i]
            parent2 = population[i + 1] if i + 1 < len(population) else population[0]

            if random.random() < self.ga_params['crossover_rate']:
                # 单点交叉
                point = random.randint(1, len(parent1) - 1)
                child1 = parent1[:point] + parent2[point:]
                child2 = parent2[:point] + parent1[point:]
                offspring.extend([child1, child2])
            else:
                # 不交叉，直接复制
                offspring.extend([parent1, parent2])

        return offspring[:len(population)]

    def mutate(self, population):
        """变异操作"""
        for i in range(len(population)):
            for j in range(len(population[i])):
                if random.random() < self.ga_params['mutation_rate']:
                    # 对第j个基因进行变异
                    supplier = self.selected_suppliers[j]
                    max_qty = supplier['capacity'] * 1.2
                    population[i][j] = random.uniform(0, max_qty)

        return population

    def optimize_transport_plan(self):
        """优化转运方案，最小化总损耗"""
        transport_plan = []

        # 为每周的订购计划制定转运方案
        for week_plan in self.order_plan:
            week = week_plan['week']
            orders = week_plan['orders']

            # 按供应商分组汇总
            supplier_orders = {}
            for order in orders:
                supplier_id = order['supplier_id']
                if supplier_id not in supplier_orders:
                    supplier_orders[supplier_id] = {
                        'total_quantity': 0,
                        'material_type': order['material_type']
                    }
                supplier_orders[supplier_id]['total_quantity'] += order['quantity']

            # 为每个供应商分配转运商
            weekly_transport = []
            for supplier_id, details in supplier_orders.items():
                # 找到损耗率最低的转运商
                best_transporter = self.find_best_transporter(details['material_type'])

                # 计算需要的运输次数
                total_qty = details['total_quantity']
                trips_needed = max(1, int(np.ceil(total_qty / self.transporter_capacity)))

                # 分配转运商
                weekly_transport.append({
                    'week': week,
                    'supplier_id': supplier_id,
                    'transporter_id': best_transporter['id'],
                    'material_type': details['material_type'],
                    'total_quantity': total_qty,
                    'trips': trips_needed,
                    'loss_rate': best_transporter['loss_rate']
                })

            transport_plan.append(weekly_transport)

        self.transport_plan = transport_plan
        return transport_plan

    def find_best_transporter(self, material_type):
        """为特定材料类型找到损耗率最低的转运商"""
        # 假设转运商数据中包含材料类型和对应的损耗率
        # 这里简化处理，选择总体损耗率最低的转运商
        sorted_transporters = self.transporter_data.sort_values('损耗率')
        return sorted_transporters.iloc[0].to_dict()

    def write_results_to_templates(self):
        """将结果写入附件A和B模板"""
        # 写入附件A (订购方案)
        self.write_order_plan_to_excel()

        # 写入附件B (转运方案)
        self.write_transport_plan_to_excel()

    def write_order_plan_to_excel(self):
        """将订购方案写入附件A"""
        # 创建一个副本，避免修改原始模板
        output_path = self.data_paths['output_a']

        # 读取模板并保留格式
        book = load_workbook(self.data_paths['template_a'])

        # 假设按材料类型分sheet存储
        material_sheets = {
            'A': 'A类原材料订购方案',
            'B': 'B类原材料订购方案',
            'C': 'C类原材料订购方案'
        }

        for material, sheet_name in material_sheets.items():
            if sheet_name not in book.sheetnames:
                continue

            sheet = book[sheet_name]
            # 找到数据开始的位置 (跳过前5行说明)
            start_row = 5

            # 收集该材料类型的所有订购数据
            material_orders = []
            for week_plan in self.order_plan:
                week = week_plan['week']
                for order in week_plan['orders']:
                    if order['material_type'] == material:
                        material_orders.append({
                            'week': week,
                            'supplier_id': order['supplier_id'],
                            'quantity': order['quantity']
                        })

            # 将数据转换为数据框并按周和供应商排序
            df = pd.DataFrame(material_orders)
            if not df.empty:
                df = df.pivot(index='supplier_id', columns='week', values='quantity').fillna(0)

                # 写入数据到Excel
                for r, (supplier_id, row) in enumerate(df.iterrows(), start=start_row + 1):
                    sheet.cell(row=r, column=1, value=supplier_id)  # 供应商ID
                    for c, week in enumerate(df.columns, start=2):
                        sheet.cell(row=r, column=c, value=row[week])

            # 确保保留最后一行的求和公式
            # (假设最后一行已经有公式，这里不做修改)

        # 保存结果
        book.save(output_path)
        print(f"订购方案已保存至: {output_path}")

    def write_transport_plan_to_excel(self):
        """将转运方案写入附件B"""
        # 创建一个副本，避免修改原始模板
        output_path = self.data_paths['output_b']

        # 读取模板并保留格式
        book = load_workbook(self.data_paths['template_b'])

        # 假设按材料类型分sheet存储
        material_sheets = {
            'A': 'A类原材料转运方案',
            'B': 'B类原材料转运方案',
            'C': 'C类原材料转运方案'
        }

        for material, sheet_name in material_sheets.items():
            if sheet_name not in book.sheetnames:
                continue

            sheet = book[sheet_name]
            # 找到数据开始的位置 (跳过前5行说明)
            start_row = 5

            # 收集该材料类型的所有转运数据
            material_transports = []
            for week_transports in self.transport_plan:
                for transport in week_transports:
                    if transport['material_type'] == material:
                        material_transports.append({
                            'week': transport['week'],
                            'supplier_id': transport['supplier_id'],
                            'transporter_id': transport['transporter_id'],
                            'quantity': transport['total_quantity'],
                            'trips': transport['trips']
                        })

            # 将数据转换为数据框并按周和供应商排序
            df = pd.DataFrame(material_transports)
            if not df.empty:
                # 这里需要根据模板的具体格式调整
                row_idx = start_row
                for _, row in df.iterrows():
                    row_idx += 1
                    sheet.cell(row=row_idx, column=1, value=row['week'])  # 周数
                    sheet.cell(row=row_idx, column=2, value=row['supplier_id'])  # 供应商ID
                    sheet.cell(row=row_idx, column=3, value=row['transporter_id'])  # 转运商ID
                    sheet.cell(row=row_idx, column=4, value=row['quantity'])  # 数量
                    sheet.cell(row=row_idx, column=5, value=row['trips'])  # 运输次数

            # 确保保留最后一行的求和公式
            # (假设最后一行已经有公式，这里不做修改)

        # 保存结果
        book.save(output_path)
        print(f"转运方案已保存至: {output_path}")

    def analyze_results(self):
        """分析订购方案和转运方案的实施效果"""
        # 计算总采购成本
        total_cost = 0
        material_counts = {'A': 0, 'B': 0, 'C': 0}

        for week_plan in self.order_plan:
            for order in week_plan['orders']:
                material_type = order['material_type']
                qty = order['quantity']
                total_cost += qty * self.cost_coefficients[material_type]
                material_counts[material_type] += qty

        # 计算总损耗
        total_loss = 0
        total_transported = 0

        for week_transports in self.transport_plan:
            for transport in week_transports:
                qty = transport['total_quantity']
                loss_rate = transport['loss_rate'] / 100  # 转换为小数
                total_loss += qty * loss_rate
                total_transported += qty

        # 计算库存波动
        inventory_levels = [self.min_inventory]  # 初始库存
        for week_plan in self.order_plan:
            total_supply = sum(
                order['quantity'] * self.material_conversion[order['material_type']]
                for order in week_plan['orders']
            )
            next_inventory = max(
                self.min_inventory,
                inventory_levels[-1] + total_supply - week_plan['demand']
            )
            inventory_levels.append(next_inventory)

        inventory_variation = np.std(inventory_levels)

        # 输出分析结果
        print("\n===== 方案实施效果分析 =====")
        print(f"1. 供应商数量: {len(self.selected_suppliers)}")
        print(f"2. 总采购成本 (相对值): {total_cost:.2f}")
        print(f"3. 原材料采购量:")
        for material, count in material_counts.items():
            print(f"   - {material}类: {count:.2f} 立方米")
        print(f"4. 总运输量: {total_transported:.2f} 立方米")
        print(f"5. 总损耗量: {total_loss:.2f} 立方米")
        print(f"6. 损耗率: {total_loss / total_transported * 100:.2f}%")
        print(f"7. 库存标准差 (波动程度): {inventory_variation:.2f}")

        # 绘制库存变化图
        plt.figure(figsize=(12, 6))
        plt.plot(range(len(inventory_levels)), inventory_levels, 'b-', marker='o')
        plt.axhline(y=self.min_inventory, color='r', linestyle='--', label='最低库存')
        plt.title('24周库存变化趋势')
        plt.xlabel('周数')
        plt.ylabel('库存水平 (等效立方米)')
        plt.grid(True)
        plt.legend()
        plt.savefig('inventory_trend.png')
        print(f"\n库存变化趋势图已保存为: inventory_trend.png")

        return {
            'supplier_count': len(self.selected_suppliers),
            'total_cost': total_cost,
            'material_counts': material_counts,
            'total_transported': total_transported,
            'total_loss': total_loss,
            'loss_rate': total_loss / total_transported * 100,
            'inventory_variation': inventory_variation
        }


if __name__ == "__main__":
    # 定义数据文件路径
    data_paths = {
        'topsis_results': '供应商TOPSIS评价结果.xlsx',
        'supplier_data': '附件1.xlsx',
        'transporter_data': '附件2.xlsx',
        'demand_forecast': '期望供货量预测结果.xlsx',
        'template_a': '附件A.xlsx',
        'template_b': '附件B.xlsx',
        'output_a': '附件A_结果.xlsx',
        'output_b': '附件B_结果.xlsx'
    }

    # 验证文件是否存在
    for name, path in data_paths.items():
        if name not in ['output_a', 'output_b'] and not os.path.exists(path):
            print(f"警告: 未找到文件 {path}，请检查路径是否正确")

    # 创建优化器实例
    optimizer = SupplyChainOptimizer(data_paths)

    # 执行供应商选择
    print("===== 开始供应商选择 =====")
    optimizer.select_suppliers()

    # 优化订购计划
    print("\n===== 开始订购计划优化 =====")
    optimizer.optimize_order_plan()

    # 优化转运计划
    print("\n===== 开始转运计划优化 =====")
    optimizer.optimize_transport_plan()

    # 写入结果到模板
    print("\n===== 写入结果到Excel =====")
    optimizer.write_results_to_templates()

    # 分析结果
    optimizer.analyze_results()

    print("\n===== 所有优化完成 =====")
    print(f"订购方案结果: {data_paths['output_a']}")
    print(f"转运方案结果: {data_paths['output_b']}")
