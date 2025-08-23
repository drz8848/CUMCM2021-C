import xlrd
import xlsxwriter
import numpy as np

# 读取供应商供货量数据
excel = xlrd.open_workbook("附件1近5年402家供应商的相关数据.xlsx", "rb")
sheet = excel.sheet_by_name("供应商的供货量(m³)")

ID = []  # 供应商ID
FL = []  # 材料类型（A/B/C）
GH = []  # 原始供货量数据（每行对应一个供应商的240周数据）
DH = []  # 原始订货量数据（每行对应一个供应商的240周数据）

# 读取ID和材料类型
for r in range(1, sheet.nrows):
    ID.append(sheet.cell_value(r, 0))
    FL.append(sheet.cell_value(r, 1))

# 读取供货量数据（GH）和订货量数据（DH）
for r in range(1, sheet.nrows):
    val_gh = []
    val_dh = []
    for c in range(2, sheet.ncols):
        val_gh.append(sheet.cell_value(r, c))  # 供货量
        # 假设订货量数据来自另一列（此处按文档逻辑补充）
        val_dh.append(sheet.cell_value(r, c))  # 实际需替换为订货量列
    GH.append(tuple(val_gh))
    DH.append(tuple(val_dh))

# 计算期望供货量（按24周周期，取10个周期的有效数据）
GH_T = []  # 存储每个供应商24周的期望供货量
for r in range(len(GH)):
    val = []
    for j in range(24):  # 24周周期
        CMP1 = []  # 订货量对比（需≥90%）
        CMP2 = []  # 供货量数据
        for i in range(10):  # 10个周期
            k = i * 24 + j  # 对应周期的第j周
            CMP1.append(DH[r][k])
            CMP2.append(GH[r][k])
        # 筛选有效数据：供货量/订货量>0.9，且在均值3倍以内
        AVE = np.mean(CMP2)
        GH_max = 0
        for i in range(10):
            if CMP1[i] == 0:
                continue
            if (CMP2[i] / CMP1[i] > 0.9) and (CMP2[i] <= 3 * AVE):
                if CMP2[i] > GH_max:
                    GH_max = CMP2[i]
        val.append(GH_max)
    GH_T.append(tuple(val))

# 输出期望供货量到Excel
workbook = xlsxwriter.Workbook("期望供货量.xlsx")
worksheet = workbook.add_worksheet()
# 写入表头
worksheet.write(0, 0, "供应商ID")
for j in range(24):
    worksheet.write(0, j + 1, f"第{j+1}周")
# 写入数据
for r in range(len(ID)):
    worksheet.write(r + 1, 0, ID[r])
    for j in range(24):
        worksheet.write(r + 1, j + 1, GH_T[r][j])
workbook.close()

import numpy as np
import xlrd
import xlsxwriter

# 读取期望供货量数据
excel = xlrd.open_workbook("期望供货量.xlsx","rb")
sheet = excel.sheet_by_name("Sheet1")
n = 402  # 供应商总数
w = 24   # 规划周数
C = 28488  # 期望产能（考虑损耗后）

# 初始化变量
FL = []  # 材料类型
ID = []  # 供应商ID
GHL = []  # 期望供货量（转换为产能）
top50 = [228, 360, 139, 107, 150, 339, 281, 274, 328, 130, 307, 329, 138, 355, 267, 305, 193, 351, 142, 347, 246, 283, 3, 303, 36, 45, 77, 291, 73, 207, 209]  # 问题一筛选的前50家供应商索引（0开始）
DP = np.zeros(n)  # DP[i]表示选i个供应商时的最小产能缺口
S = [[] for _ in range(n)]  # S[i]表示选i个供应商时的最优组合

# 读取数据并转换为产能（材料→产能：A/0.6，B/0.66，C/0.72）
for r in range(1, sheet.nrows):
    ID.append(sheet.cell_value(r, 0))
    fl = sheet.cell_value(r, 1)
    FL.append(fl)
    val = []
    for c in range(1, sheet.ncols):
        s = sheet.cell_value(r, c)
        if fl == 'A':
            s = s / 0.6
        elif fl == 'B':
            s = s / 0.66
        elif fl == 'C':
            s = s / 0.72
        val.append(s)
    GHL.append(tuple(val))

# 贪心函数：选择k个供应商，按权重Z优化
def T(k, Z, name):
    name2 = []
    ObjL = np.zeros(w)  # 当前各周产能
    for _ in range(k):
        minObj = float('inf')
        now_j = -1
        # 遍历前50家供应商，选择未被选中且缺口最小的
        for j in top50:
            if j in name or j in name2:
                continue
            now_Obj = 0
            # 计算选择该供应商后的产能缺口
            for z in range(w):
                temp_Obj = ObjL[z] + GHL[j][z]
                now_Obj += Z[z] * max(C - temp_Obj, 0)
            if now_Obj < minObj:
                minObj = now_Obj
                now_j = j
        # 更新产能和选中列表
        if now_j != -1:
            name2.append(now_j)
            for z in range(w):
                ObjL[z] += GHL[now_j][z]
    return name2

# 权重更新函数：根据当前产能缺口调整权重
def get_new_Z(name):
    cha = np.zeros(w)
    ObjL = np.zeros(w)
    # 计算当前产能
    for j in name:
        for z in range(w):
            ObjL[z] += GHL[j][z]
    # 计算缺口（可跨周补充）
    for z in range(w-1):
        cha[z] = max(C - ObjL[z], 0)
        if cha[z] < 0:
            cha[z+1] += cha[z]
            cha[z] = 0
    cha[w-1] = max(C - ObjL[w-1], 0)
    s = np.sum(cha)
    if s == 0:
        return np.ones(w) / w
    newZ = cha / s
    return newZ

# 计算产能缺口函数
def GetObj(name):
    ObjL = np.zeros(w)
    # 计算初始产能
    for j in name:
        for z in range(w):
            ObjL[z] += GHL[j][z]
    # 跨周调整（提前两周备料）
    for z in range(1, w):
        if ObjL[z] < C:
            x = C - ObjL[z]
            # 从z-1周调货
            if ObjL[z-1] > C:
                if x < ObjL[z-1] - C:
                    ObjL[z-1] -= x
                    ObjL[z] += x
                else:
                    y = ObjL[z-1] - C
                    ObjL[z-1] -= y
                    ObjL[z] += y
            # 从z-2周调货
            if z >= 2 and ObjL[z] < C:
                x = C - ObjL[z]
                if ObjL[z-2] > C:
                    if x < ObjL[z-2] - C:
                        ObjL[z-2] -= x
                        ObjL[z] += x
                    else:
                        y = ObjL[z-2] - C
                        ObjL[z-2] -= y
                        ObjL[z] += y
    # 计算总缺口
    now_Obj = sum(max(C - ObjL[z], 0) for z in range(w))
    return now_Obj

# 主程序：动态规划+贪心求解
if __name__ == "__main__":
    # 初始化DP（设为极大值）
    for i in range(n):
        DP[i] = float('inf')
    # 逐步增加供应商数量，寻找最小缺口
    for i in range(1, 50):
        Sel1 = S[i-1].copy() if i > 1 else []
        Z = get_new_Z(Sel1)
        Sel2 = T(1, Z, Sel1)  # 贪心选1个供应商
        Sel3 = Sel1 + Sel2
        # 计算当前缺口
        obj = GetObj(Sel3)
        if obj < DP[i]:
            DP[i] = obj
            S[i] = Sel3.copy()
        # 动态规划：拆分供应商组合
        for r in range(1, i):
            Sel_a = S[r].copy()
            Z2 = get_new_Z(Sel_a)
            Sel_b = T(i - r, Z2, Sel_a)
            Sel_total = Sel_a + Sel_b
            obj_total = GetObj(Sel_total)
            if obj_total < DP[i]:
                DP[i] = obj_total
                S[i] = Sel_total.copy()
        # 若缺口为0，停止搜索（找到最少供应商）
        if DP[i] == 0:
            print(f"最少供应商数量：{i}")
            print(f"供应商索引：{S[i]}")
            break

    # 输出结果到Excel
    workbook = xlsxwriter.Workbook("供应商规划结果.xlsx")
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, "供应商数量")
    worksheet.write(0, 1, "最小产能缺口")
    worksheet.write(0, 2, "供应商组合（索引）")
    for i in range(1, 50):
        worksheet.write(i, 0, i)
        worksheet.write(i, 1, DP[i])
        worksheet.write(i, 2, str(S[i]))
    workbook.close()

import random
import numpy as np
import xlrd
import xlsxwriter

# 按单位成本排序的键函数
def takeCB(elem):
    return elem[0]

# 初始化参数
n = 402  # 供应商总数
w = 24   # 规划周数
C = 28488  # 期望产能
ID = []  # 供应商ID
FL = []  # 材料类型
GHL = []  # 期望供货量（原始单位：m³）
Seln = []  # 问题二确定的27家供应商索引
JIEGUO = np.zeros((n, w))  # 订货量结果（JIEGUO[r][c]表示第r个供应商第c周的订货量）

# 读取期望供货量数据
excel = xlrd.open_workbook("期望供货量.xlsx", "rb")
sheet = excel.sheet_by_name("Sheet1")
for r in range(1, sheet.nrows):
    ID.append(sheet.cell_value(r, 0))
    FL.append(sheet.cell_value(r, 1))
    val = []
    for c in range(1, sheet.ncols):
        val.append(sheet.cell_value(r, c))
    GHL.append(tuple(val))

# 问题二确定的27家供应商索引（0开始，来自供应商规划结果.xlsx）
namelist = [228, 360, 139, 329, 107, 307, 281, 339, 328, 274, 355, 138, 142, 130, 150, 394, 351, 305, 267, 306, 193, 36, 283, 347, 246, 30, 364]

# 订货量分配函数
def DOIT(PX, week):
    global JIEGUO
    for L in PX:
        cb, j, z, zh = L  # 单位成本、供应商索引、材料类型、消耗量
        JIEGUO[j][week] += 1 / zh  # 按产能需求分配订货量

# 主程序：离散化贪心规划订货量
if __name__ == "__main__":
    for week in range(w):  # 逐周规划
        PX = []  # 存储离散化的供货单元（[单位成本, 供应商索引, 材料类型, 消耗量]）
        maxl = C * 2  # 最大离散化单元数
        # 遍历27家供应商
        for j in namelist:
            fl = FL[j]
            now_GH = int(GHL[j][week])  # 本周期望供货量
            # 确定材料参数（消耗量、采购单价）
            if fl == 'A':
                zh = 0.6
                jg = 1.2
            elif fl == 'B':
                zh = 0.66
                jg = 1.1
            elif fl == 'C':
                zh = 0.72
                jg = 1.0
            else:
                continue
            # 离散化处理（1m³为1单元）
            for k in range(now_GH):
                # 计算单位产能成本（含稳定性权重）
                wdd = 1 if k <= GHL[j][week] else 0.001  # 稳定性权重
                cb = (jg + 0.5 * jg) / (zh * wdd)  # 单位产能成本（含存储成本）
                PX.append([cb, j, fl, zh])
        # 按单位成本升序排序（优先选低成本）
        PX.sort(key=takeCB)
        # 选择足够单元满足本周产能
        tag = 0
        k = 0
        while tag < C and k < len(PX):
            tag += 1 / PX[k][3]
            k += 1
        # 分配订货量
        PX_now = PX[:k]
        DOIT(PX_now, week)
        # 剩余单元留到下周（加存储成本）
        PX_remain = PX[k:]
        for p in PX_remain:
            p[0] += 0.1  # 存储成本增加

    # 输出订货量结果到Excel
    workbook = xlsxwriter.Workbook("订单量规划结果.xlsx")
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, "供应商ID")
    for c in range(w):
        worksheet.write(0, c + 1, f"第{c+1}周订货量(m³)")
    for r in range(n):
        worksheet.write(r + 1, 0, ID[r])
        for c in range(w):
            worksheet.write(r + 1, c + 1, JIEGUO[r][c])
    workbook.close()

import numpy as np
import xlrd
import xlsxwriter

# 初始化参数
num = 402  # 供应商总数
w = 24     # 规划周数
ID = []    # 供应商ID
FL = []    # 材料类型
AW = []    # 每周A类材料总订货量
BW = []    # 每周B类材料总订货量
CW = []    # 每周C类材料总订货量

# 读取期望供货量数据（获取材料类型）
excel_gh = xlrd.open_workbook("期望供货量.xlsx", "rb")
sheet_gh = excel_gh.sheet_by_name("Sheet1")
for r in range(1, sheet_gh.nrows):
    ID.append(sheet_gh.cell_value(r, 0))
    FL.append(sheet_gh.cell_value(r, 1))

# 读取订单量规划结果
excel_order = xlrd.open_workbook("订单量规划结果.xlsx", "rb")
sheet_order = excel_order.sheet_by_name("Sheet1")

# 逐周汇总ABC材料订货量
for c in range(1, sheet_order.ncols):
    AN = 0  # 本周A类总订货量
    BN = 0  # 本周B类总订货量
    CN = 0  # 本周C类总订货量
    for r in range(1, sheet_order.nrows):
        s = sheet_order.cell_value(r, c)
        fl = FL[r-1]  # FL索引从0开始，sheet行从1开始
        if fl == 'A':
            AN += s
        elif fl == 'B':
            BN += s
        elif fl == 'C':
            CN += s
    AW.append(AN)
    BW.append(BN)
    CW.append(CN)

# 输出汇总结果到Excel（横向：周数；纵向：ABC）
workbook = xlsxwriter.Workbook("ABC_quanju.xlsx")
worksheet = workbook.add_worksheet()
worksheet.write(1, 0, "A类材料")
worksheet.write(2, 0, "B类材料")
worksheet.write(3, 0, "C类材料")
for i in range(w):
    worksheet.write(0, i + 1, f"第{i+1}周")
    worksheet.write(1, i + 1, AW[i])
    worksheet.write(2, i + 1, BW[i])
    worksheet.write(3, i + 1, CW[i])
workbook.close()

# 转换为纵向表格（用于后续转运规划）
workbook_test = xlsxwriter.Workbook("ABCtestT2.xlsx")
worksheet_test = workbook_test.add_worksheet()
worksheet_test.write(0, 0, "周数")
worksheet_test.write(0, 1, "A类订货量(m³)")
worksheet_test.write(0, 2, "B类订货量(m³)")
worksheet_test.write(0, 3, "C类订货量(m³)")
for i in range(w):
    worksheet_test.write(i + 1, 0, i + 1)
    worksheet_test.write(i + 1, 1, AW[i])
    worksheet_test.write(i + 1, 2, BW[i])
    worksheet_test.write(i + 1, 3, CW[i])
workbook_test.close()

import numpy as np
import xlrd
import xlsxwriter

# 转运商可靠度排序（T3>T6>T2>T8>T4>T1>T7>T5，对应索引0-7）
X = [2, 5, 1, 7, 3, 0, 6, 4]
chushi = np.zeros(8)  # 初始分配值
w = 24  # 规划周数

# 读取ABC订货量数据
excel = xlrd.open_workbook("ABCtestT2.xlsx", "rb")
sheet = excel.sheet_by_name("Sheet1")

# 初始化工作簿
workbook = xlsxwriter.Workbook("转运分配值.xlsx")
worksheet = workbook.add_worksheet()

# 逐周计算转运分配初始值
for z in range(w):
    # 读取本周ABC订货量
    A = int(sheet.cell_value(z + 1, 1))
    B = int(sheet.cell_value(z + 1, 2))
    C = int(sheet.cell_value(z + 1, 3))
    NOW = [A, B, C]  # 当前ABC需求量
    FP = np.zeros((3, 8))  # FP[0][k]：第k个转运商A类分配量

    f = 0  # 材料类型索引（0=A，1=B，2=C）
    j = 0  # 转运商索引
    while f < 3:
        i = X[j]  # 按可靠度选择转运商
        # 计算转运商剩余容量（6000 - 已分配A/B/C）
        remain = 6000 - (FP[0][i] + FP[1][i] + FP[2][i])
        if NOW[f] <= remain:
            # 需求量≤剩余容量，全部分配
            FP[f][i] += NOW[f]
            NOW[f] = 0
            f += 1
            j = 0  # 重置转运商索引，下一种材料重新选可靠的
        else:
            # 需求量>剩余容量，先填满，剩余量继续分配
            FP[f][i] += remain
            NOW[f] -= remain
            j += 1
            if j >= 8:
                j = 0  # 所有转运商遍历完，重新开始

    # 写入当前周的分配值（每行对应1周，3行ABC）
    for i in range(3):
        for k in range(8):
            worksheet.write(z * 3 + i + 1, k + 1, FP[i][k])
    # 写入周数标签
    worksheet.write(z * 3 + 1, 0, f"第{z + 1}周-A")
    worksheet.write(z * 3 + 2, 0, f"第{z + 1}周-B")
    worksheet.write(z * 3 + 3, 0, f"第{z + 1}周-C")

# 写入表头
worksheet.write(0, 0, "周数-材料")
for k in range(8):
    worksheet.write(0, k + 1,
                    f"转运商{T3 if k == 0 else T6 if k == 1 else T2 if k == 2 else T8 if k == 3 else T4 if k == 4 else T1 if k == 5 else T7 if k == 6 else T5}")  # 此处T3等需替换为实际转运商ID
workbook.close()

import numpy as np
import xlrd
import xlsxwriter

# 初始化参数
num = 402  # 供应商总数
w = 24  # 规划周数
C = 28488  # 期望产能
ID = []  # 供应商ID
FL = []  # 材料类型
YS = np.zeros((num + 1, w * 8 + 1))  # YS[r][c]：第r个供应商第c个转运商-周的转运量

# 读取期望供货量数据（获取供应商ID和材料类型）
excel_gh = xlrd.open_workbook("期望供货量.xlsx", "rb")
sheet_gh = excel_gh.sheet_by_name("Sheet1")
for r in range(1, sheet_gh.nrows):
    ID.append(sheet_gh.cell_value(r, 0))
    FL.append(sheet_gh.cell_value(r, 1))


# 读取转运分配值
def getFP(week):
    excel = xlrd.open_workbook("转运分配值.xlsx", "rb")
    sheet = excel.sheet_by_name("Sheet1")
    FPJZ = []
    # 读取当前周的ABC分配值（3行）
    for j in range(3):
        row = week * 3 + j + 1
        val = []
        for i in range(1, 9):
            val.append(sheet.cell_value(row, i))
        FPJZ.append(val)
    return FPJZ


# 0-1背包函数
def bag(n, c, w, v):
    res = np.zeros((n + 1, c + 1))
    for i in range(1, n + 1):
        for j in range(1, c + 1):
            if j >= w[i - 1]:
                res[i][j] = max(res[i - 1][j], res[i - 1][j - w[i - 1]] + v[i - 1])
            else:
                res[i][j] = res[i - 1][j]
    return res


# 背包结果回溯（显示选中的材料）
def show(n, c, w, res, r_list, week, k):
    used = []
    j = c
    for i in range(n, 0, -1):
        if res[i][j] > res[i - 1][j]:
            j -= w[i - 1]
            used.append(r_list[i - 1])
            # 更新转运量记录
            YS[int(r_list[i - 1])][(week - 1) * 8 + k] += w[i - 1]
    return used


# 主程序：逐周规划转运方案
if __name__ == "__main__":
    # 转运商可靠度排序（对应索引0-7）
    Tpaixu = [2, 5, 1, 7, 3, 0, 6, 4]
    # 读取订单量数据
    excel_order = xlrd.open_workbook("订单量规划结果.xlsx", "rb")
    sheet_order = excel_order.sheet_by_name("Sheet1")

    for week in range(1, w + 1):  # 逐周处理
        FP = getFP(week - 1)  # 获取本周转运分配初始值
        A = []  # 本周A类材料供应商-订货量（[s, r]，s=订货量，r=供应商索引）
        B = []  # 本周B类材料供应商-订货量
        C = []  # 本周C类材料供应商-订货量

        # 读取本周各供应商订货量，按材料分类
        for r in range(1, sheet_order.nrows):
            s = sheet_order.cell_value(r, week)
            fl = FL[r - 1]
            if fl == 'A' and s > 0:
                A.append([s, r - 1])  # r-1为供应商索引（0开始）
            elif fl == 'B' and s > 0:
                B.append([s, r - 1])
            elif fl == 'C' and s > 0:
                C.append([s, r - 1])

        # 按材料类型和转运商可靠度规划
        for mat_idx, mat_list in enumerate([A, B, C]):
            used = []  # 已分配的供应商
            for k in Tpaixu:  # 按转运商可靠度排序
                if FP[mat_idx][k] <= 0:
                    continue
                # 当前转运商的分配量
                xx = int(min(FP[mat_idx][k], 6000))
                # 筛选未分配的供应商
                mat_available = [[s, r] for s, r in mat_list if r not in used]
                if not mat_available:
                    continue
                # 提取重量（订货量）和价值（订货量，价值=重量）
                w_list = [x[0] for x in mat_available]
                v_list = w_list.copy()
                r_list = [x[1] for x in mat_available]
                n = len(w_list)
                # 0-1背包求解
                res = bag(n, xx, w_list, v_list)
                # 回溯结果，更新已分配供应商
                used += show(n, xx, w_list, res, r_list, week, k)

        # 贪心处理剩余未分配材料（填补空缺）
        for mat_idx, mat_list in enumerate([A, B, C]):
            for s, r in mat_list:
                if r in used:
                    continue
                # 寻找剩余容量的转运商
                for k in Tpaixu:
                    remain = 6000 - sum(YS[r][(week - 1) * 8 + k]
                    '] for k' in range(8))
                    if remain > 0:
                        alloc = min(s, remain)
                    YS[r][(week - 1) * 8 + k] += alloc
                    s -= alloc
                    if s <= 0:
                        used.append(r)
                    break

    # 输出转运结果到Excel
    workbook = xlsxwriter.Workbook("YS_T2.xlsx")
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, "供应商ID")
    for c in range(w * 8):
        week = c // 8 + 1
        trans = c % 8 + 1
        worksheet.write(0, c + 1, f"第{week}周-转运商{trans}")
    for r in range(num):
        worksheet.write(r + 1, 0, ID[r])
        for c in range(w * 8):
            worksheet.write(r + 1, c + 1, YS[r][c])
    workbook.close()

import numpy as np
import xlrd
import xlsxwriter

# 初始化参数
num = 402  # 供应商总数
w = 24     # 规划周数
ID = []    # 供应商ID
FL = []    # 材料类型
AW = []    # 每周各转运商A类转运量
BW = []    # 每周各转运商B类转运量
CW = []    # 每周各转运商C类转运量

# 读取期望供货量数据（获取材料类型）
excel_gh = xlrd.open_workbook("期望供货量.xlsx", "rb")
sheet_gh = excel_gh.sheet_by_name("Sheet1")
for r in range(1, sheet_gh.nrows):
    ID.append(sheet_gh.cell_value(r, 0))
    FL.append(sheet_gh.cell_value(r, 1))

# 读取转运结果数据
excel_ys = xlrd.open_workbook("YS_T2.xlsx", "rb")
sheet_ys = excel_ys.sheet_by_name("Sheet1")

# 逐周逐转运商汇总ABC转运量
for week in range(w):
    aw = [0] * 8  # 本周8个转运商A类转运量
    bw = [0] * 8  # 本周8个转运商B类转运量
    cw = [0] * 8  # 本周8个转运商C类转运量
    # 遍历每个转运商
    for trans in range(8):
        col = week * 8 + trans + 1  # 转运商列索引
        # 遍历每个供应商
        for r in range(1, sheet_ys.nrows):
            s = sheet_ys.cell_value(r, col)
            fl = FL[r-1]
            if fl == 'A':
                aw[trans] += s
            elif fl == 'B':
                bw[trans] += s
            elif fl == 'C':
                cw[trans] += s
    AW.append(aw)
    BW.append(bw)
    CW.append(cw)

# 输出汇总结果到Excel
workbook = xlsxwriter.Workbook("转运ABC.xlsx")
worksheet = workbook.add_worksheet()
worksheet.write(1, 0, "A类材料")
worksheet.write(2, 0, "B类材料")
worksheet.write(3, 0, "C类材料")
# 写入表头（周数-转运商）
k = 1
for week in range(w):
    for trans in range(8):
        worksheet.write(0, k, f"第{week+1}周-转运商{trans+1}")
        k += 1
# 写入数据
for week in range(w):
    for trans in range(8):
        col = week * 8 + trans + 1
        worksheet.write(1, col, AW[week][trans])
        worksheet.write(2, col, BW[week][trans])
        worksheet.write(3, col, CW[week][trans])
workbook.close()

