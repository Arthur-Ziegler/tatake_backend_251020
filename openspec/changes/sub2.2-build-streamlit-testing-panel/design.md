# Design: Streamlit 测试面板独立功能

## 核心设计原则
1. **功能独立**：所有页面不依赖任务管理
2. **数据驱动**：列表中提供一键操作按钮
3. **简洁展示**：表格 + JSON 双视图

## 技术栈
- 复用提案 1 的基础架构（API 客户端、状态管理器）
- Streamlit 原生组件（无需额外依赖）

## 核心模块设计

### 1. 智能聊天页面（pages/3_💬_智能聊天.py）

#### 布局设计
```
┌────────────────────────────────────┐
│ 左侧（30%）    │ 右侧（70%）        │
│ ┌────────────┐ │ ┌──────────────┐ │
│ │ 会话列表    │ │ │ 聊天记录     │ │
│ │ - 会话1    │ │ │ 👤 你：xxx   │ │
│ │ - 会话2    │ │ │ 🤖 AI：yyy  │ │
│ │ [创建会话]  │ │ │              │ │
│ └────────────┘ │ │ 输入框 [发送] │ │
│                │ │ └──────────────┘ │
└────────────────────────────────────┘
```

#### 实现
```python
# 左侧：会话列表
col1, col2 = st.columns([3, 7])

with col1:
    st.subheader("会话列表")
    sessions = api_client.get("/api/v1/chat/sessions")

    for session in sessions["data"]:
        if st.button(session["title"], key=session["id"]):
            st.session_state.current_session_id = session["id"]

    if st.button("创建会话"):
        title = st.text_input("会话标题")
        api_client.post("/api/v1/chat/sessions", json={"title": title})

# 右侧：聊天记录
with col2:
    if st.session_state.get("current_session_id"):
        session_id = st.session_state.current_session_id
        messages = api_client.get(f"/api/v1/chat/sessions/{session_id}/messages")

        # 消息列表
        with st.container(height=400):
            for msg in messages["data"]:
                if msg["role"] == "user":
                    st.markdown(f"**👤 你**: {msg['content']}")
                else:
                    st.markdown(f"**🤖 AI**: {msg['content']}")

        # 输入框
        user_input = st.text_input("输入消息", key="chat_input")
        if st.button("发送"):
            api_client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": user_input})
            st.rerun()
```

### 2. 奖励系统页面（pages/5_🎁_奖励系统.py）

#### 标签页设计
```python
tab1, tab2, tab3, tab4 = st.tabs(["奖品目录", "我的奖品", "我的材料", "可用配方"])

with tab1:  # 奖品目录
    catalog = api_client.get("/api/v1/rewards/catalog")
    for reward in catalog["data"]:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(reward["name"])
        with col2:
            st.write(f"积分：{reward['points_cost']}")
        with col3:
            if st.button("兑换", key=f"redeem_{reward['id']}"):
                api_client.post(f"/api/v1/rewards/exchange/{reward['id']}")
                st.success("兑换成功")

with tab2:  # 我的奖品
    my_rewards = api_client.get("/api/v1/rewards/my-rewards")
    st.dataframe(my_rewards["data"])

with tab3:  # 我的材料
    materials = api_client.get("/api/v1/rewards/materials")
    st.dataframe(materials["data"])

with tab4:  # 可用配方
    recipes = api_client.get("/api/v1/rewards/recipes")
    for recipe in recipes["data"]:
        st.write(f"配方：{recipe['name']}")
        if st.button("兑换", key=f"recipe_{recipe['id']}"):
            api_client.post(f"/api/v1/rewards/recipes/{recipe['id']}/redeem")
            st.success("兑换成功")
```

### 3. 积分系统页面（pages/6_💰_积分系统.py）

#### 实现
```python
# 积分余额
st.title("💰 积分系统")
balance = api_client.get(f"/api/v1/points/my-points?user_id={st.session_state.user_id}")
st.metric(label="当前积分", value=balance["data"]["balance"], delta=None)

# 积分流水
st.subheader("积分流水")
if st.button("查看流水"):
    transactions = api_client.get(f"/api/v1/points/transactions?user_id={st.session_state.user_id}")
    st.dataframe(transactions["data"])
```

### 4. 用户管理页面（pages/8_👤_用户管理.py）

#### 实现
```python
st.title("👤 用户管理")

# 个人资料
st.subheader("个人资料")
profile = api_client.get("/api/v1/users/profile")
st.json(profile["data"])

# 反馈表单
st.subheader("提交反馈")
feedback = st.text_area("反馈内容")
if st.button("提交"):
    api_client.post("/api/v1/users/feedback", json={"content": feedback})
    st.success("反馈提交成功")
```

## 关键技术决策

### 决策 1：为什么聊天页面使用两列布局？
**原因**：
- 符合用户习惯（类似微信）
- 左侧会话列表便于快速切换
- 右侧聊天记录和输入框集中在一起

### 决策 2：为什么奖励系统使用标签页？
**原因**：
- 四个功能紧密关联（奖品、材料、配方）
- 标签页减少页面滚动，提升体验
- 便于快速切换查看不同数据

### 决策 3：为什么积分系统单独一个页面？
**原因**：
- 积分是独立的核心数据
- 流水记录可能很长，需要独立空间
- 与奖励系统解耦，便于维护

## 性能考虑
- **按需加载**：只在页面切换时加载数据
- **会话缓存**：当前会话 ID 存储在 session_state
- **流水分页**：如果流水记录过多，可以考虑分页（第二阶段优化）

## 用户体验优化
- **聊天实时刷新**：发送消息后使用 `st.rerun()` 刷新界面
- **兑换成功提示**：积分兑换、材料兑换后显示成功提示
- **表格展示**：使用 `st.dataframe` 展示列表数据，支持排序和筛选
