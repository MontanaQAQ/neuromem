## 论文《Think-in-Memory: Recalling and Post-thinking Enable LLMs with Long-Term Memory》- TiM（Think-in-Memory）总结：

一、记忆数据结构

TiM 的记忆数据结构是一个 基于哈希表的外部记忆缓存（Memory Cache M），其核心特征如下：
存储内容：以“归纳性思想”（Inductive Thoughts）为基本单元。每个 thought 是一个关系三元组形式的自然语言句子（如 “(The Wandering Earth, has, stunning visuals)”）。
组织方式：采用 Locality-Sensitive Hashing (LSH) 构建哈希索引，使得语义相近的 thoughts 被映射到相同的哈希桶（group）中。
接口设计：
插入接口（Insert）：支持多种插入策略（在文中体现为通过 LLM 生成新 thought 后插入），但本质上统一为“将新 thought 经 LSH 映射后加入对应桶”。
检索接口（Retrieve）：固定为两阶段检索：
1. LSH 快速定位候选桶；
2. 在桶内计算相似度，返回 top-k thoughts。
删除接口（Forget / Remove）：固定为基于逻辑一致性判断（如去除矛盾句）的删除操作，由 LLM 判断后执行。

二、记忆操作（按阶段划分）
1. 插入前操作（Pre-Insert Operation）
触发时机：在 LLM 生成当前轮次的响应（Response）之后、执行“后思考”（Post-thinking）之前。
主要任务：
对当前 Q-R 对（用户提问与 LLM 回答）进行后思考，生成新的归纳性 thought（如通过 In-context Learning 提示 LLM 提取关系三元组）。
可查询记忆数据结构（例如检查是否已有类似 thought），但不能修改。
限制：仅允许读取，不允许写入或删除。
输出：待插入的新 thought(s)。

2. 插入操作（Insert）
输入：由插入前操作生成的新 thought(s)。
执行方式：
对每个新 thought 计算 LSH 哈希值；
将其插入对应哈希桶中（即 memory cache 的 value list）。
插入方法：文中仅使用一种插入逻辑（直接追加至桶内），但框架允许扩展（如带权重插入、条件插入等）。
不可见性：插入过程对上层透明，外部无法干预插入策略。

3. 插入后操作（Post-Insert Operation）
触发时机：插入完成后立即执行。
主要任务：对所在哈希桶内的 thoughts 进行记忆优化，包括：
Forget：调用 LLM 判断并移除矛盾或反事实的 thoughts；
Merge：调用 LLM 合并同一实体的多个相关 thoughts（如 “John works as actor/director/writer” → 合并为一句）。
操作限制：
仅允许一次完整的“检索-删除-再插入”流程：即先读取整个桶的内容，经 LLM 处理后，清空原桶并重新插入优化后的 thoughts。
不允许多次独立修改。
目的：模拟人类记忆的“整合与遗忘”机制，保持记忆一致性与简洁性。

4. 检索前操作（Pre-Retrieve Operation）
触发时机：收到新用户提问（Query）后、正式检索前。
主要任务：
对 Query 进行预处理（如嵌入向量化，用于后续 LSH 计算）；
可能进行意图识别或关键词提取（隐含在 embedding 过程中）。
严格限制：不允许访问记忆数据结构。
输出：处理后的查询表示（embedding 或文本）。

5. 检索操作（Retrieve）
输入：预处理后的 Query。
执行流程（固定不可干预）：
1. 用相同 LSH 函数计算 Query 的哈希索引；
2. 定位到对应桶；
3. 在桶内计算 Query 与所有 thoughts 的相似度；
4. 返回 top-k 最相关 thoughts。
外部不可控：上层无法指定“检索哪些字段”或“换检索算法”。

6. 检索后操作（Post-Retrieve Operation）
主要任务：
将检索到的 top-k thoughts 拼接成 prompt，供 LLM 生成最终回答；
允许多次查询记忆数据结构（例如：若初始结果不足，可基于初步结果再次检索相关桶——尽管原文未显式这么做，但框架允许）；
可进行结果重排序、去冗余、上下文融合等。
灵活性：此阶段是构建最终输入给 LLM 的关键环节，可多次交互记忆库以丰富上下文。
输出：增强后的 prompt，包含历史 thoughts。

## 论文《MemoryBank: Enhancing Large Language Models with Long-Term Memory》- MemoryBank 总结：

一、记忆数据结构

MemoryBank 的记忆数据结构是一个多层级、带语义摘要的持久化存储系统，其核心组成如下：
存储内容
原始对话记录（Raw Conversations）：按时间戳保存的多轮用户-AI交互历史。
事件摘要（Event Summaries）：
每日事件摘要（Daily Event Summary）
全局事件摘要（Global Event Summary）
用户画像（User Portrait）：
每日人格/情绪分析（Daily Personality Insight）
全局人格画像（Global User Portrait）

这些内容共同构成一个结构化但非扁平的记忆库，支持细粒度（原始对话）和粗粒度（摘要、画像）信息共存。
接口定义

操作类型 方法说明
---------- ---------
插入（Insert） 支持多种插入策略：<br>1. 直接追加原始对话<br>2. 触发 LLM 生成当日事件摘要与人格分析后插入<br>（论文中通过固定 prompt 调用 LLM 实现摘要与画像更新）
检索（Retrieve） 使用稠密向量检索（Dense Retrieval）：<br>- 所有记忆片段（包括原始对话、事件摘要）预先用编码器（如 MiniLM / Text2vec）编码并 FAISS 索引<br>- 查询时对当前上下文编码，在索引中近似最近邻搜索，返回 top-k 相关记忆片段<br>- 固定策略：仅基于语义相似度，外部不可干预检索逻辑
删除（Delete） 由记忆更新机制触发：<br>- 基于 Ebbinghaus 遗忘曲线模型计算每个记忆项的“记忆强度”<br>- 当强度低于阈值时，从存储中移除<br>- 删除操作是内部自动执行，不对外暴露手动删除接口

二、记忆操作（按阶段划分）
1. 插入前操作（Pre-Insert）
功能：对即将插入的原始对话进行预处理，并决定采用何种插入方式。
允许操作：仅可检索记忆数据结构（例如查询已有用户画像以辅助新摘要生成）。
实际行为（论文中）：
获取当前对话上下文
（可选）检索全局用户画像或历史事件摘要，用于指导后续摘要生成
不修改记忆结构
示例：在插入新对话前，系统可能检索“当前用户是否已有性格标签”，以决定是否需重新生成人格分析。
2. 插入操作（Insert）
输入：原始对话 +（可选）插入方法标识（如“仅存原始”或“生成摘要后存”）
执行：
将原始对话按时间戳写入存储
若启用摘要机制，则调用 LLM 生成：
当日事件摘要（Prompt: “Summarize the events and key information…”）
当日人格洞察（Prompt: “Based on the dialogue, summarize personality traits…”）
将新摘要/画像插入对应层级
特点：插入方法在论文中是固定的流程（即总是生成摘要），但架构上可扩展为多种策略。
3. 插入后操作（Post-Insert）
功能：优化记忆结构，主要是触发记忆更新机制（遗忘与强化）。
允许操作：仅允许一次“检索 → 删除 → 插入”序列。
实际行为：
对所有记忆项（特别是刚插入的）计算记忆强度 $ S $
初始 $ S = 1 $
若被检索（即在后续对话中被 recall），则 $ S \leftarrow S + 1 $，$ t \leftarrow 0 $
根据 $ R = e^{-t/S} $ 计算保留概率
对低强度记忆项执行删除
（理论上可重新插入压缩后的记忆，但论文未实现此步）
此阶段体现“人类式遗忘”：不重要的旧记忆被自动清理，重要记忆因被频繁调用而强化。

4. 检索前操作（Pre-Retrieve）
功能：对用户当前 query 进行预处理（如意图识别、关键词提取）。
限制：不允许访问记忆数据结构。
论文实现：
直接将用户当前 utterance 作为检索 query
无额外预处理（即默认 query = user input）
符合“不允许访问记忆”的约束。
5. 检索操作（Retrieve）
输入：预处理后的 query
执行：
使用共享编码器 $ E(\cdot) $ 将 query 编码为向量 $ h_c $
在 FAISS 索引中检索最相似的 top-k 记忆片段（包括原始对话、事件摘要）
返回原始记忆内容（非嵌入向量）
关键限制：检索逻辑完全由系统内部决定（基于语义相似度），外部无法指定“只查画像”或“只查上周对话”。
6. 检索后操作（Post-Retrieve）
功能：整合检索结果，构建最终 prompt。
允许操作：可多次查询记忆数据结构，拼接不同类型记忆。
论文实现：
将检索到的相关记忆片段
额外查询全局用户画像（Global User Portrait）
额外查询全局事件摘要（Global Event Summary）
将三者拼接成增强 prompt，送入 LLM 生成回复
Prompt 结构示例：

[Meta Prompt]
[Global User Portrait: "open-minded, curious..."]
[Global Event Summary: "discussed Python learning, gift preferences..."]
[Relevant Memory: "On 04-28, user asked about quicksort..."]
[Current Query: "Do you remember the gifts she like?"]

此阶段利用了记忆结构的多层性，实现个性化响应。

## 论文 MemGPT 总结：

一、记忆数据结构（Memory Data Structures）
所有结构均提供 插入、检索、删除 三种接口（即使某些操作是隐式的），且支持长期或短期记忆存储。

1. 工作上下文（Working Context）
性质：结构化、持久、高优先级长期记忆。
内容示例：{"name": "Alice", "birthday": "Feb 7", "ex-boyfriend": "James"}
接口行为：
插入：主动插入（如 append 新事实）；也可触发 replace（通过插入后操作）。
检索：按关键词/语义匹配返回条目（内部实现）。
删除：移除特定条目（通常由 replace 流程调用）。
2. FIFO 消息队列（FIFO Message Queue）
性质：非结构化、临时、顺序性短期记忆。
内容示例：[User: "Hi", Agent: "Hello!", User: "My birthday is Feb 7", ...]
接口行为：
插入：被动插入（新消息自动追加到尾部）。
检索：只能按顺序访问（LLM 看到整个队列内容，但无法随机查询某条）——但从系统角度看，“检索”表现为“读取当前队列全部内容”，符合固定策略。
删除：当超出容量时，自动从头部驱逐最旧消息（即 FIFO 驱逐），属于固定删除策略。

它存储记忆（对话历史）；
支持插入（append）、检索（读全部）、删除（evict head）；
插入方法为被动（系统控制）；
检索与删除策略固定（顺序读、先进先出驱逐）。
3. 召回存储（Recall Storage）
性质：持久化外部记忆，保存所有曾进入 FIFO 的消息。
作用：当 FIFO 驱逐了某条消息，仍可通过检索从 Recall Storage 恢复。
接口行为：
插入：被动（消息进入 FIFO 时同步写入）。
检索：基于语义/关键词搜索（固定策略）。
删除：通常不支持物理删除，但可通过逻辑覆盖或归档实现“软删除”。

二、记忆操作（Memory Operations）

所有操作严格遵循四阶段模型，无缓存、无状态传递：即使某阶段已查询过记忆，下一阶段若需相同信息，必须重新检索。
1. 插入前操作（Pre-Insertion）
职责：对待插入的记忆内容进行预处理（如从用户话语中提取事实：“我换了新号码” → 提取“phone number updated”）。
决策：决定使用哪种插入方法（例如是否需要替换旧号码？还是新增一条？）。
约束：只能读取记忆数据结构（如查询 Working Context 中是否已有 phone number 条目），不能写入或删除。
2. 插入操作（Insertion）
执行：根据插入前的决策，调用记忆数据结构的基础插入接口。
特点：
仅支持原子写入，如 append(new_fact)。
不包含 replace（replace 是复合操作，不属于基础插入）。
可分为主动或被动：
主动插入：由插入前操作明确指定目标（如“将此事实写入 Working Context”）。
被动插入：由系统自动分配位置（如新对话消息自动 append 到 Recall Storage）。
3. 插入后操作（Post-Insertion）
职责：优化记忆结构的一致性与有效性（如去重、更新、摘要）。
典型操作：replace(old, new)。
执行流程：一次且仅一次“检索 → 删除 → 插入”序列。
例：检索到“Boyfriend: James”，删除该条目，插入“Ex-boyfriend: James”。
约束：不允许多次修改；replace 是此阶段的核心体现。
4. 检索前操作（Pre-Retrieval）
职责：解析用户提问，提取检索意图（如“你们第一次见面在哪？” → 提取关键词 “first meeting location”）。
约束：完全禁止访问任何记忆数据结构。纯语言层面处理。
5. 检索操作（Retrieval）
执行：调用记忆数据结构的固定检索接口（如 recall_storage.search(query)）。
约束：
检索策略（如向量相似度阈值、返回数量）由系统内部决定。
外部（包括 LLM）无法指定如何检索，只能提供查询字符串。
6. 检索后操作（Post-Retrieval）
职责：整合检索结果，构造最终 prompt。
权限：
允许多次访问记忆数据结构（可再次检索、甚至触发新的插入/删除）。
可拼接来自 Working Context 和 Recall Storage 的信息。
最终输出为结构化上下文，供 LLM 生成回复。
例：检索到三条关于“六旗乐园”的历史消息，再查询 Working Context 确认用户偏好，最终拼接成：“你和 James 在六旗乐园相识，你喜欢过山车……”


## 论文《A-MEM: Agentic Memory for LLM Agents》- A-Mem总结：

一、记忆数据结构

A-MEM 的记忆数据结构以 “笔记（note）” 为基本存储单元，每个笔记是一个结构化的对象，包含多个语义属性和一个嵌入向量。具体字段包括：
ci：原始交互内容（content）
ti：时间戳（timestamp）
Ki：LLM 生成的关键词（keywords）
Gi：LLM 生成的标签（tags）
Xi：LLM 生成的上下文描述（contextual description）
ei：由文本编码器生成的稠密嵌入向量（embedding）
Li：与其他记忆建立的链接集合（links）

此外，整个记忆库 M = {m₁, m₂, ..., mₙ} 可视为一个动态演化的知识图谱，其中节点是笔记，边是通过语义分析建立的链接。
接口定义
插入接口：支持一种主要插入方法——将新笔记加入集合 M，并触发后续操作。
检索接口：基于查询嵌入 eq 与所有 ei 的余弦相似度，返回 top-k 最相关笔记。
删除接口：虽未显式强调删除操作，但在“记忆演化”中隐含了“替换”行为（即删除旧版本并插入新版本），可视为逻辑删除+插入。

二、记忆操作流程
1. 插入前操作（Pre-insertion）
功能：对原始交互内容进行预处理，生成结构化记忆字段（Ki, Gi, Xi）。
执行方式：调用 LLM，使用提示模板 Ps1，输入为原始内容 ci 和时间 ti。
限制：仅允许读取现有记忆库（用于上下文感知？），但论文中此阶段并未实际查询历史记忆。因此，在未经优化的原始设计中，插入前操作不访问记忆数据结构。
输出：完整的结构化笔记 mi（不含链接 Li 和嵌入 ei）。

2. 插入操作（Insertion）
类型：被动插入。
新记忆被添加到集合 M 中，其存储位置不由插入前操作决定，而是由底层向量数据库（如 FAISS）根据嵌入 ei 自动索引。
过程：
1. 计算嵌入 ei = f_enc(concat(ci, Ki, Gi, Xi))
2. 将完整笔记 mi 存入记忆库 M
特点：插入本身不涉及复杂路由或分区策略，完全依赖嵌入空间的自动组织。

3. 插入后操作（Post-insertion）
功能：优化记忆结构，包括建立链接（Link Generation）和演化已有记忆（Memory Evolution）。
步骤：
(a) 链接生成（Link Generation）：
使用新记忆的嵌入 en 检索 top-k 最近邻 Mn_near（一次检索）
调用 LLM（Ps2）判断是否应与这些邻居建立链接 → 更新新记忆的 Li
(b) 记忆演化（Memory Evolution）：
对 Mn_near 中的每个 mj，调用 LLM（Ps3）决定是否更新其上下文、关键词或标签
若需更新，则*删除旧 mj，插入新版本 m\j（即 replace 操作）
限制：整个过程仅允许一次检索（用于获取 Mn_near），后续的删除与插入均基于该结果。

4. 检索前操作（Pre-retrieval）
功能：对当前查询 q 进行预处理。
执行：计算查询嵌入 eq = f_enc(q)
限制：不允许访问记忆数据结构。
输出：嵌入向量 eq，用于后续检索。

5. 检索操作（Retrieval）
机制：基于余弦相似度，返回 top-k 最相似的记忆笔记。
控制权：检索逻辑完全由系统内部决定（固定为向量相似度检索），外部无法干预检索策略。
输出：M_retrieved = {mi rank(sq,i) ≤ k}

6. 检索后操作（Post-retrieval）
功能：处理检索结果，构建最终 prompt。
操作：
可多次查询记忆数据结构：例如，对每个检索到的记忆 mi，进一步获取其链接记忆 L_i（即“同一 box 中的相关记忆”）
将原始检索结果 + 链接记忆拼接成上下文丰富的 prompt
目的：增强多跳推理能力，利用记忆网络的拓扑结构。

## 论文《Memory OS of AI Agent》总结：

一、记忆数据结构（Memory Data Structures）
MemoryOS 中的记忆数据结构由三层存储单元构成，每层都支持插入、检索、删除三种基本接口。这些结构本身也包含一些全局性摘要信息（如 persona、segment summary），属于记忆数据结构的一部分。

1. Short-Term Memory (STM)
结构：固定长度的 FIFO 队列，每个元素是一个 dialogue page（含 Q, R, T, metachain）
插入方法：仅一种——尾部追加（被动插入，由结构决定位置）
检索方法：返回全部内容（固定策略）
删除方法：FIFO 弹出（固定策略）
2. Mid-Term Memory (MTM)
结构：Segment-Page 架构
Segment：按主题聚类的对话段落集合，含语义摘要（LLM 生成）
Page：原始 dialogue pages
插入方法：
被动插入：新 page 根据 Fscore 与现有 segment 匹配，若 >θ 则归入；否则新建 segment
检索方法：
两阶段固定流程：先按 Fscore 选 top-m segments，再在 segment 内按语义相似度选 top-k pages
删除方法：
基于 Heat Score 的低热淘汰（固定策略）
3. Long-term Personal Memory (LPM)
结构：包含 User Persona 与 Agent Persona
User Persona = {User Profile（静态）, User KB（FIFO 队列）, User Traits（90维动态向量）}
Agent Persona = {Agent Profile（静态）, Agent Traits（FIFO 队列）}
插入方法：
被动插入：当 MTM segment 的 Heat ≥ τ 时，自动提取信息更新 User KB / Traits / Agent Traits
插入到 KB/Traits 使用 FIFO（固定位置）
检索方法：
固定：对 KB/Traits 检索 top-10 最相关条目（基于语义相似度）
删除方法：
FIFO 自动覆盖（固定策略）

二、记忆操作（Memory Operations）
按照你定义的六个阶段，MemoryOS 的操作可映射如下：

1. 插入前操作（Pre-insertion）
功能：预处理待插入的记忆数据，并决定如何插入（主动 or 被动）
允许操作：仅可 检索 记忆数据结构（无缓存，结果不保留）
实例：
在 STM → MTM 插入前：
检索 MTM 所有 segments，计算新 page 与各 segment 的 Fscore（Eq. 3）
决定是否新建 segment 或归入现有 segment（被动插入决策）
在 MTM → LPM 插入前：
检索 segment 的 Heat Score（需访问 Nvisit, Linteraction, Rrecency）
判断是否 ≥ τ（决定是否触发插入）

2. 插入操作（Insertion）
功能：执行实际写入
方式：
STM：append to queue（被动）
MTM：归入 segment 或新建（被动）
LPM：向 User KB / Traits / Agent Traits 写入（被动，FIFO）
无主动插入：所有插入均由结构规则驱动，非由外部指定位置

3. 插入后操作（Post-insertion）
功能：优化记忆结构（如 replace、evict、reset）
允许操作：一次 “检索 → 删除 → 插入” 组合（即 replace 类操作）
实例：
MTM 容量超限时：检索所有 segment 的 Heat，删除最低者（delete）
LPM 更新后：将原 segment 的 Linteraction 重置为 0（相当于逻辑 delete + update Heat）
User KB / Agent Traits 满时：FIFO 自动删除最旧条目（隐式 replace）

4. 检索前操作（Pre-retrieval）
功能：预处理用户 query（如嵌入、关键词提取）
限制：不允许访问 任何记忆数据结构
实例：
将用户 query 编码为向量（用于后续语义匹配）
提取关键词（用于 Fscore 中的 Jaccard 计算）

5. 检索操作（Retrieval）
功能：直接返回结果
限制：不允许外部干预检索策略
行为：
STM：返回全部 pages
MTM：固定两阶段（segment → page）
LPM：固定 top-10 语义匹配

6. 检索后操作（Post-retrieval）
功能：整合多源记忆，构建 prompt
允许操作：多次查询 记忆结构，并拼接结果
实例：
先从 STM 取近期上下文
再从 MTM 取相关 segments/pages
再从 LPM 取 persona、traits、KB
拼接成最终 prompt 输入 LLM
额外查询示例：
若 MTM 返回某 segment，可再次查询其关联的 LPM traits 以增强个性化

## 论文《HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models》总结：

一、记忆数据结构
存储结构
核心结构：一个无模式（schemaless）的知识图谱（KG），由节点（名词短语/命名实体）和边（三元组关系 + 同义词边）构成。
辅助结构：
一个 |N| × |P| 的矩阵 P，记录每个 KG 节点在原始段落中的出现频次（用于后续检索打分）。
节点特异性（Node Specificity）：每个节点附带一个本地统计量 s
i=1/∣P_i​∣，其中 P_i是包含该节点的段落数。
注：全局摘要记忆（如 RAPTOR 中的树状摘要）未被采用，HippoRAG 的记忆结构是扁平的、基于原始文本提取的 KG，不包含高层抽象节点。

接口设计
插入接口
插入方法：仅一种——被动插入。
段落通过 LLM 执行 OpenIE 提取三元组（主谓宾形式），直接添加到 KG。
同时使用检索编码器（如 Contriever/ColBERTv2）计算节点间余弦相似度，若超过阈值 τ，则添加同义词边（synonymy edges）。
插入位置不由插入前操作决定，而是由 KG 自身结构（节点是否已存在、是否需新建）和编码器相似度自动决定 → 属于被动插入。
检索接口（固定）
输入：用户查询（query）。
输出：排序后的段落列表。
内部机制不可干预：系统内部执行 NER → 节点链接 → PPR → 段落打分 → 返回 top-k。
删除接口（固定）
论文中未提及任何显式的删除操作。
知识更新通过“增量添加边/节点”实现，而非删除旧内容。
因此，删除接口在当前设计中缺失或未被使用。
二、记忆操作
1. 插入前操作（Pre-insertion）
功能：对输入段落进行预处理，决定如何插入。
实际行为：
使用 LLM 对段落执行两步提示：先抽取命名实体，再基于这些实体引导 OpenIE 提取更相关的三元组。
此过程不访问现有 KG（即不查询已有节点是否存在），因此未利用记忆数据结构进行决策。
结论：虽有预处理，但未执行“仅允许检索”的约束下的查询，本质上是纯文本处理，未体现“主动插入”所需的查询-决策闭环。

→ 不符合“主动插入”定义，仅为被动插入的前置文本解析

2. 插入后操作（Post-insertion）
功能：优化记忆结构，可执行一次“检索-删除-插入”组合。
实际行为：
论文未描述任何插入后的结构调整。


3. 检索前操作（Pre-retrieval）
功能：预处理用户查询，不允许访问记忆数据结构。
实际行为：
使用 LLM 对查询执行命名实体识别（NER），提取“查询命名实体” C_q。
此过程仅依赖 LLM，不访问 KG 或段落库。
结论：完全符合定义。
✅ 存在且合规

4. 检索后操作（Post-retrieval）
功能：处理检索结果，允许多次查询记忆结构以拼接 prompt。
实际行为：
HippoRAG 仅返回排序后的段落列表。
未对检索结果进行二次查询、扩展或重组。
最终 prompt 构建由上层 QA 系统完成（如将 top-2 段落拼接送入 LLM 回答），非 HippoRAG 自身职责。
结论：检索后操作在 HippoRAG 内部缺失。
❌ 无检索后处理

（注：这属于模块边界设计，HippoRAG 定位为 retriever，非完整 RAG pipeline）

## HippoRAG 2总结：

该记忆体本质上是一个 非参数化、基于知识图谱（KG）的长期记忆系统，用于支持大语言模型（LLM）的持续学习能力。

一、记忆数据结构
存储结构：
开放知识图谱（Open Knowledge Graph, KG）：由两类节点组成：
Phrase Nodes（短语节点）：表示从文本中提取出的实体或概念（如 “Erik Hort”、“Montebello”）。
Passage Nodes（段落节点）：表示原始文档/段落，通过 “contains” 边连接到其包含的所有 Phrase Nodes。
边类型：
Relation Edges：连接主语-谓语-宾语三元组（如 (Erik Hort, born in, Montebello)）。
Synonym Edges：连接语义相似的 Phrase Nodes（通过嵌入相似度阈值判断）。
Context Edges（即 “contains”）：连接 Passage Node 到其包含的所有 Phrase Nodes。
注：全局摘要（如 RAPTOR 的摘要树、GraphRAG 的社区摘要）并未被 HippoRAG 2 采用，因此 不属于其记忆数据结构的一部分。
接口定义：
插入接口（Insert）：
方法：被动插入（由记忆数据结构自身决定存储位置）。
具体流程：LLM 对新 passage 执行 OpenIE 提取三元组 → 构建新的 Phrase Nodes 和 Relation Edges → 将 passage 作为 Passage Node 加入图中，并通过 “contains” 边连接相关 Phrase Nodes。
同时，检索编码器对所有 Phrase Nodes 进行相似度计算，建立 Synonym Edges。
仅一种插入方法（无主动插入机制）。
检索接口（Retrieve）：
方法固定：基于 Personalized PageRank (PPR) 的图遍历。
输入：查询（query）。
输出：排序后的 Passage Nodes（即原始段落）。
检索过程完全由内部 PPR 算法驱动，外部无法干预“如何检索”。
删除接口（Delete）：
论文未提及显式删除操作。
可推断：不支持删除（或删除不是设计重点），符合大多数 RAG 系统“只增不删”的特性。

二、记忆操作
1. 插入前操作（Pre-Insertion）
功能：预处理新记忆数据（即新 passage）。
操作内容：
调用 LLM 对 passage 执行 OpenIE，提取结构化三元组。
（隐含）可能对 passage 进行分块或标准化。
是否访问记忆数据结构？
否。此阶段仅处理输入数据，不涉及对现有 KG 的检索（尽管技术上可行，但论文未描述利用已有 KG 信息来指导插入）。
✅ 符合“仅允许检索”的规则，但实际未执行任何检索。
2. 插入操作（Insertion）
如上所述，执行被动插入：
将新 Phrase Nodes、Relation Edges、Passage Node 及 Context Edges 添加到 KG。
同时运行嵌入模型，为新 Phrase Nodes 与现有节点计算相似度，添加 Synonym Edges。
3. 插入后操作（Post-Insertion）
功能：优化记忆结构。
论文中是否存在？
不存在显式的插入后优化。
无 replace、合并、去重、图压缩等操作。
Synonym Edge 的构建虽在插入时完成，但属于插入本身，而非后续优化。
是否执行“检索-删除-插入”？
否。无任何此类操作描述。
❌ 缺失插入后操作。
4. 检索前操作（Pre-Retrieval）
功能：预处理用户查询（query）。
操作内容：
使用嵌入模型将 query 编码。
执行 Query-to-Triple 匹配：计算 query 与图中所有三元组的相似度，选出 top-k 三元组。
是否访问记忆数据结构？
否。虽然匹配对象是图中的 triples，但按你的定义，“检索前操作不允许访问记忆数据结构”——此处存在语义边界问题。
严格来说，Query-to-Triple 是一次对记忆数据结构的检索（读取所有 triples 并打分）。
但按论文流程，这一步被视为 检索阶段的起始部分，而非独立的“预处理”。
⚠️ 若严格按照你的规则（检索前完全不可访问记忆结构），则 HippoRAG 2 违反此约束。
但若将“Query-to-Triple”视为检索操作的内部第一步，则符合。
此处我们采纳后者：检索前操作仅指纯 query 改写/增强，而 HippoRAG 2 无此类操作。
因此：检索前操作为空。
5. 检索操作（Retrieval）
方法固定：PPR 图搜索。
流程：
1. 从 Query-to-Triple 结果中提取 Phrase Nodes 作为 seed nodes。
2. 同时加入 top 相似 Passage Nodes 作为额外 seeds。
3. 运行 PPR，得到所有 Passage Nodes 的 PageRank 分数。
4. 返回 top-k Passage Nodes（即原始段落）。
外部是否可干预？
否。完全由内部算法决定。

✅ 符合“检索时直接返回结果，不允许外部决定如何检索”。
6. 检索后操作（Post-Retrieval）
功能：处理检索结果，构造 prompt。
操作内容：
将 top-k 检索到的 passages 拼接为上下文。
送入 LLM 生成最终答案。
是否允许多次查询记忆结构？
论文未描述在检索后再次查询 KG。
所有上下文仅来自 PPR 返回的 passages。
无二次检索、无图遍历扩展、无动态拼接其他记忆片段。
❌ 未充分利用“允许多次查询”的能力，仅做简单拼接。
但符合最低要求（至少返回了记忆数据）。


##  LD-Agent 总结：

一、记忆数据结构
LD-Agent 的记忆数据结构由 长时记忆库（Long-term Memory Bank） 和 短时记忆缓存（Short-term Memory Cache） 共同构成。

存储内容：
长时记忆库：存储的是经过摘要模块处理后的事件摘要向量，形式为 {ϕ(t_j,o_j)∣j=1,…,l}，其中 t_j是事件发生时间，o_j是摘要文本，ϕ(⋅) 是文本编码器（如 MiniLM）。
短时记忆缓存：存储当前会话的原始对话上下文，形式为 {(t_i,u_i)}，带有时间戳。
接口设计：
插入接口：
支持两种插入方法：
被动插入：当短时记忆缓存超时（超过600秒），系统自动触发摘要生成，并将结果被动插入到长时记忆库中（由记忆数据结构内部逻辑决定插入位置）。
主动插入：在训练或推理过程中，若事件摘要模块显式输出新事件摘要，则可由上层逻辑主动插入至长时记忆库（由插入前操作决定）。
检索接口（固定）：
使用基于嵌入的检索机制，结合语义相似度、话题重叠度和时间衰减系数计算综合得分（见公式 (2)），返回 top-k 或满足阈值的记忆项。
删除接口（固定）：
虽未显式提及“删除”操作，但通过替换（replace） 实现等效功能（见下文插入后操作）。此外，短时记忆缓存在超时后会被清空，可视作一种批量删除。
注：全局的事件摘要本身是记忆数据结构的一部分——它不是原始对话，而是经过压缩、结构化的记忆表示。

二、记忆操作
1. 插入前操作（Pre-insertion）
职责：
对原始对话片段进行预处理，判断是否构成一个可记忆的“事件”。
决定是否需要插入、以及采用哪种插入策略（主动 or 被动）。
约束：
仅允许对记忆数据结构进行检索（例如查询最近一次对话是否已有关于同一话题的记忆，以避免冗余）。
不得修改记忆数据结构。
在 LD-Agent 中的体现：
短时记忆缓存的时间检查（判断是否超时）属于插入前操作的一部分。
若未超时，则不触发插入；若超时，则调用摘要模块生成 o=A(M_S​)，准备插入。
2. 插入操作（Insertion）
执行：
根据插入前操作的决策，将新记忆项（如 (ϕ(t,o))）写入长时记忆库。
方法：
被动插入：由系统定时/事件驱动触发（如会话间隔超时）。
主动插入：由外部模块（如训练流程）显式调用。
3. 插入后操作（Post-insertion）
职责：
优化记忆数据结构，例如去重、合并、压缩或替换旧记忆。
只允许一次“检索 → 删除 → 插入”原子操作序列。
在 LD-Agent 中的体现：
Replace 操作即为此类：若新事件与已有记忆高度重合（如相同话题、相近时间），系统可在插入后检索旧记忆、删除之，并插入更新后的摘要。
虽文中未显式实现 replace，但其框架支持此类优化（因其记忆库为可写集合，且摘要模块可动态更新）。
4. 检索前操作（Pre-retrieval）
职责：
对当前用户输入（query）进行预处理，例如提取关键词、识别话题、标准化表述。
约束：
不允许访问记忆数据结构。
在 LD-Agent 中的体现：
提取 query 中的名词集合 V_q 用于话题重叠计算（公式 (1)），此步骤在检索前完成，且不依赖记忆库内容。
5. 检索操作（Retrieval）
执行：
输入预处理后的 query，直接返回最相关的记忆项 m=ψ(M_L,γ)。
约束：
检索策略完全由记忆数据结构内部决定（语义+话题+时间衰减），外部不得干预检索过程。
若无记忆满足语义阈值 γ=0.5，则返回 “No relevant memory”。
6. 检索后操作（Post-retrieval）
职责：
对检索结果进行后处理与整合，形成可用于生成的上下文 prompt。
允许多次查询记忆数据结构（例如补充相关记忆、验证一致性等），并将多个记忆片段拼接。
在 LD-Agent 中的体现：
检索到的记忆 m 会与短时记忆 M_S、用户 persona P_u 、代理 persona P_a 一起拼接成生成器的输入（见公式 (4)）。
此过程可能涉及多次记忆查询（如分别检索用户相关事件与代理相关事件），最终融合为统一 prompt。

## Self-Controlled Memory (SCM) 总结：

一、记忆数据结构（Memory Data Structure）

在 SCM 框架中，记忆数据结构由 Memory Stream（记忆流） 实现。
存储内容
每个记忆项（memory item）包含以下字段：
interaction index（交互序号）
observation（用户输入）
system response（系统回复）
memory summarization（对该轮交互的摘要）
interaction embedding（语义向量，由 observation + response 拼接后经 text-embedding-ada-002 生成）
注：全局摘要记忆（如 hierarchical summarization 中的高层 summary）虽未显式作为独立字段存储，但通过“memory summarization”字段和分层处理机制隐式支持，可视为记忆数据结构的一部分。
接口定义

操作类型 是否存在 说明
-------- -------- ------
插入（Insert） ✅ 存在 支持 被动插入：新交互（observation + response）在 Response Generation 步骤结束后自动追加至 Memory Stream 末尾。论文未提及主动指定插入位置的机制，因此 仅有一种插入方法（追加）。
检索（Retrieve） ✅ 存在 固定为 基于嵌入的 top-K 检索：使用当前 observation 的嵌入作为 query，计算与所有 memory items 的 cosine similarity（相关性）+ recency score，取 rank_score 最高的 K 项返回。外部无法干预检索逻辑。
删除（Delete） ❌ 未体现 论文中 未描述任何显式的删除操作。记忆流是只增不减的（append-only），无淘汰、覆盖或显式移除机制。

二、记忆操作（Memory Operations）

按照您定义的五阶段操作模型，逐项分析 SCM 框架是否实现及其实现方式：
1. 插入前操作（Pre-Insertion Operation）
功能：预处理待插入的记忆数据，并决定如何插入。
SCM 中对应环节：Response Generation 后、写入记忆流前。
行为分析：
对刚完成的交互（observation + response）调用 Memory Summarization Prompt（图3）生成摘要。
调用 embedding 模型生成 interaction embedding。
允许检索记忆数据结构：论文未在此阶段使用历史记忆辅助摘要或嵌入生成，因此 虽允许但未实际执行检索。
结论：✅ 存在，负责生成摘要与嵌入；插入方式固定为追加（被动插入）。
2. 插入操作（Insertion）
功能：将预处理后的记忆项写入记忆数据结构。
SCM 中对应环节：Workflow Step 6（“incorporating the current interaction... into the memory stream”）。
行为分析：
将包含原始交互、摘要、嵌入的记忆项 追加 到 Memory Stream。
插入方法唯一（append），无路由或位置选择逻辑。
结论：✅ 存在，仅支持被动插入（追加）。
3. 插入后操作（Post-Insertion Operation）
功能：优化记忆结构，允许一次“检索-删除-插入”组合操作（如 replace）。
SCM 中对应环节：无。
行为分析：
论文 未描述任何在插入后对已有记忆项进行修改、合并、压缩或删除的行为。
虽有“Memory Summarization”，但它是针对单轮交互的摘要，而非对历史记忆的重构。
Replace 操作未被实现：例如，不会用新摘要替换旧记忆，也不会合并相似记忆。
结论：❌ 不存在。记忆流是静态追加的，无插入后优化。
4. 检索前操作（Pre-Retrieval Operation）
功能：预处理用户提问（query），不允许访问记忆数据结构。
SCM 中对应环节：Memory Controller 的第一判断（图5 prompt）。
行为分析：
使用 prompt 判断当前 user input 是否需要激活记忆（“yes/no”）。
若需激活，则直接使用原始 user input（或其嵌入）作为检索 query。
全程未查询 Memory Stream，符合约束。
结论：✅ 存在，负责决定是否触发检索，并准备 query。
5. 检索操作（Retrieval）
功能：根据 query 返回结果，检索逻辑固定，外部不可干预。
SCM 中对应环节：Memory Retrieval（Step 3）。
行为分析：
使用 observation 嵌入 + recency score 进行 top-K 排序。
返回两类记忆：Activation Memory（长期相关记忆） + Flash Memory（上一轮交互）。
检索策略完全由框架内部决定，用户/agent 无法指定过滤条件或排序规则。
结论：✅ 存在，且符合“固定检索方法”的要求。
6. 检索后操作（Post-Retrieval Operation）
功能：处理检索结果，允许多次查询并拼接成 prompt。
SCM 中对应环节：Memory Reorganization + Input Fusion（Steps 4–5）。
行为分析：
对每条激活记忆，若其长度 >800 tokens 且总 token >2000，则调用图6 prompt 判断是否可用摘要替代原文。
此判断过程 可能涉及多次查询记忆项的内容（读取原文 vs 摘要）。
最终将选中的记忆（原文或摘要）按格式拼接为背景信息，与当前 observation 融合成最终 prompt（图7）。
结论：✅ 存在，且执行了多次记忆访问与动态拼接。

## 《Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory》Mem0 总结。

一、记忆数据结构
1. 存储结构
论文提出了两种记忆数据结构：
（1）Mem0（基础版）
结构形式：以自然语言文本形式存储“事实”（salient memories），每个记忆为一个独立的文本片段（如 “Alice is vegetarian and avoids dairy.”）。
附加信息：虽然未显式说明，但从上下文可推断每条记忆可能附带时间戳或来源上下文（用于更新逻辑）。
全局摘要：系统维护一个对话级别的 全局摘要 S，作为整个对话历史的压缩表示，属于记忆数据结构的一部分。
（2）Mem0ᵍ（图增强版）
结构形式：有向标签图 $ G = (V, E, L) $
节点 $ V $：实体（如 Alice、San_Francisco），每个节点包含：
实体类型（Person, City 等）
语义嵌入向量 $ e_v $
创建时间戳 $ t_v $
边 $ E $：关系三元组 $ (v_s, r, v_d) $，如 (Alice, prefers, tofu)
标签 $ L $：节点/边的语义类型
存储后端：使用 Neo4j 图数据库实现。
✅ 结论：两种结构均明确支持 插入、检索、删除 三种基本接口。

二、记忆操作（按阶段划分）
A. 插入前操作（Pre-insertion）
功能：
预处理新对话消息对 $ (m_{t-1}, m_t) $
决定如何提取候选记忆（即“要插入什么”）
仅允许对记忆数据结构进行检索（不能修改）
Mem0 中的具体实现：
输入：新消息对 + 全局摘要 $ S $ + 最近 $ m=10 $ 条消息
调用 LLM 提取候选记忆集合 $ \Omega = \{\omega_1, ..., \omega_n\} $
检索行为：从数据库中读取 $ S $（全局摘要）和近期消息（作为上下文），但不修改任何记忆。
✅ 符合“仅允许检索”的约束。
Mem0ᵍ 中的具体实现：
使用 LLM 两阶段提取：
1. 实体识别（entities + types）
2. 关系生成（triplets）
此阶段 未访问现有图结构（即未检索已有节点/边），仅基于当前对话生成候选图元素。
⚠️ 注意：此阶段 未执行任何对记忆数据结构的检索，比规范更严格（规范允许检索，但此处未用）。属于“缺失但合理”。

B. 插入操作（Insertion）
功能：
将预处理后的记忆数据写入记忆数据结构
可提供多种插入方法（如“追加”、“覆盖”、“合并”等）
Mem0：
插入方法由 LLM 工具调用决定，共四种操作：
ADD：无相似记忆 → 新增
UPDATE：有相似且互补 → 合并
DELETE：有矛盾 → 删除旧记忆
NOOP：无需操作
插入方法非固定：由 LLM 动态选择，属于 主动插入（由插入前/中逻辑决定插入方式）。
✅ 支持多种插入方法，为主动插入。
Mem0ᵍ：
对每个新实体/关系：
计算嵌入
检索相似节点（阈值 $ t $）
若存在相似节点 → 复用；否则 → 创建新节点
建立关系边
冲突检测：若新关系与旧关系冲突，标记旧关系为“过期”（而非物理删除）
✅ 插入逻辑由系统规则驱动，但依赖语义相似性匹配，可视为 被动插入（由记忆结构自身决定是否复用节点）。
🔁 混合模式：实体创建偏被动，关系建立偏主动（由 LLM 生成）。

C. 插入后操作（Post-insertion）
功能：
优化记忆数据结构
仅允许一次“检索 → 删除 → 插入”原子操作
Mem0：
在“UPDATE”或“DELETE”操作中，系统：
1. 检索 top-$ s=10 $ 个相似记忆
2. LLM 判断是否需删除/更新
3. 执行对应操作（如删除旧记忆 + 插入新记忆）
这一过程 在单次更新循环内完成，符合“一次检索-删除-插入”约束。
✅ UPDATE 和 DELETE 即为典型的 插入后操作，用于优化一致性。
Mem0ᵍ：
冲突解决机制：当新关系与旧关系冲突时，
检索现有关系
标记旧关系为无效（逻辑删除）
插入新关系
虽未物理删除，但通过“有效性标记”实现逻辑替换。
✅ 属于插入后优化，符合规范（即使删除是逻辑的）。

D. 检索前操作（Pre-retrieval）
功能：
预处理用户提问
不允许访问记忆数据结构
Mem0 & Mem0ᵍ：
用户提问直接作为输入传给检索模块
无额外预处理（如 query expansion、rewrite 等未提及）
确实未访问记忆库
✅ 符合“不允许访问记忆数据结构”的约束。

E. 检索操作（Retrieval）
功能：
直接根据提问返回结果
不允许外部干预检索策略
Mem0：
使用向量相似性检索 top-$ k $ 记忆（作为 prompt 上下文）
检索完全由嵌入模型 + 向量数据库自动完成
Mem0ᵍ：
双路径检索：
1. 实体中心法：识别 query 中实体 → 查图 → 扩展子图
2. 语义三元组法：将 query 编码为向量 → 与所有关系三元组计算相似度 → 返回高分 triplet
检索逻辑内置于系统，外部无法指定“查哪个节点”或“走哪条路径”
✅ 检索过程封闭，符合“不允许外部决定如何检索”。

F. 检索后操作（Post-retrieval）
功能：
处理检索结果
允许多次查询记忆数据结构
拼接成最终 prompt 返回给上层 LLM
Mem0：
检索到的记忆直接拼接为 context，送入 LLM 生成答案
未进行二次检索（即只查一次）
⚠️ 缺失多次查询：虽规范允许，但实际未使用。属于“功能未用，但接口支持”。
Mem0ᵍ：
检索后可能构建子图（涉及多跳遍历）
子图构建过程隐含 多次内存访问（如从中心节点递归展开邻居）
最终将子图序列化为文本 prompt
✅ 显式支持多次查询，符合规范。

三、总结对照表

组件 Mem0 Mem0ᵍ
------ ------ --------
记忆数据结构 自然语言事实 + 全局摘要 有向标签图（实体+关系+类型+时间戳）
插入前操作 ✅ 检索摘要+近期消息，提取候选记忆 ⚠️ 未检索，仅生成候选（符合但保守）
插入方法 主动插入（LLM 决定 ADD/UPDATE/DELETE） 被动+主动混合（节点复用被动，关系生成主动）
插入后操作 ✅ UPDATE/DELETE 实现 replace ✅ 冲突标记实现逻辑 replace
检索前操作 ✅ 无访问 ✅ 无访问
检索操作 ✅ 向量检索，封闭 ✅ 双路径检索，封闭
检索后操作 ⚠️ 仅单次检索，未多次查询 ✅ 子图构建隐含多次查询

四、关键观察

1. 全局摘要 S 是记忆数据结构的一部分，在插入前被读取，用于上下文感知。
2. Replace 操作确实存在，体现为 UPDATE（Mem0）和“标记旧关系失效”（Mem0ᵍ），属于典型的插入后优化。
3. 无缓存假设成立：每次操作都重新查询（如更新时再次检索相似记忆），未依赖插入前的结果。
4. 部分操作未充分利用规范允许的能力（如检索后未多次查询 in Mem0），但这属于实现选择，不影响架构合规性。

✅ 结论：
论文中的 Mem0 和 Mem0ᵍ 均 高度契合 你提出的记忆体视角。其中 Mem0ᵍ 更充分地利用了“多次检索”和“结构化操作”的潜力，而 Mem0 则以简洁高效见长。两者在 插入后优化 和 主动/被动插入 方面均有清晰体现，整体设计严谨且符合工程可部署性要求。

## 《On Memory Construction and Retrieval for Personalized Conversational Agents》SeCom 总结：
一、记忆数据结构
定义：用于持久化存储对话历史信息的数据容器，支持三种基本接口：插入（Insert）、检索（Retrieve）、删除（Delete）。

特点：

结构形式：SECOM 使用的是分段级（segment-level）记忆单元作为基本存储单位，而非传统 turn-level（轮次级）或 session-level（会话级）。
记忆单元内容：每个 segment 是一个语义连贯、主题一致的对话片段（通过压缩式去噪和语义聚类形成），可视为一种局部摘要+原始上下文混合体。
全局摘要记忆：虽然文中未显式构建单一全局摘要，但其 segment-level 结构本身具备摘要性质（经压缩去噪），可视为分布式的“局部摘要记忆”，属于记忆数据结构的一部分。
接口说明：

插入（Insert）：支持多种策略（见下文“插入方法”）。
检索（Retrieve）：固定为基于嵌入相似度（如 MPNet 或 BM25）的 top-k 检索，输入为当前用户请求，输出为若干 memory segments。
删除（Delete）：文中未强调显式删除机制，但在“插入后操作”中可通过 replace 实现逻辑删除（即覆盖旧 segment）。
二、记忆操作
1. 插入前操作（Pre-Insert Operation）
职责：

对即将插入的原始对话历史进行预处理：包括分段（segmentation）、去噪（compression-based denoising）、语义聚类。
决定插入方式：是主动插入（指定目标位置/合并策略）还是被动插入（交由记忆结构内部规则处理）。
约束：

可检索现有记忆数据结构（例如检查是否已有相关 segment 可合并），但不能修改。
文中体现：在构建新 segment 前，系统可能需判断是否应与已有 segment 合并（如语义重叠），这需要查询当前记忆库。
✅ 示例：使用 Mistral-7B 或 RoBERTa 对连续对话轮次进行分割，识别出“关于认知偏差”的话题段落，并压缩冗余内容——此过程可能查询已有 segments 以避免重复。

2. 插入操作（Insert）
执行：

将预处理后的 segment 按指定方法写入记忆数据结构。
插入方法多样性：
被动插入：默认行为，将新 segment 作为独立单元追加到记忆库（由系统自动分配 ID 或时间戳）。
主动插入：若插入前操作检测到与某已有 segment 高度相关，则可触发“合并”或“替换建议”，但实际写入仍由插入接口完成。
📌 注意：文中未显式区分“插入方法 API”，但从设计逻辑看，SECOM 支持基于语义相似性的合并式插入（即新 segment 与旧 segment 融合），这隐含了多种插入策略。

3. 插入后操作（Post-Insert Operation）
职责：

优化记忆数据结构：例如去冗余、更新关联、执行 replace。
允许一次“检索 → 删除 → 插入”原子操作。
文中体现：

Replace 操作：当新 segment 与旧 segment 语义高度重合时，系统可删除旧 segment 并插入更新后的版本（如修正错误或补充细节）。
压缩式去噪（Compression-based Denoising）：虽主要在插入前进行，但其效果在插入后体现为更干净的记忆结构，可视为一种结构性优化。
✅ 这正是 SECOM 性能优于 baselines 的关键（Table 2 显示去除 denoising 会导致 ~9.5 分下降）。

4. 检索前操作（Pre-Retrieve Operation）
职责：

对当前用户请求进行预处理（如 query expansion、意图识别、关键词提取）。
不得访问记忆数据结构。
文中体现：

用户请求直接用于嵌入计算（如 MPNet 编码），无额外上下文注入。
未对 query 做复杂改写，符合“仅预处理提问”的约束。
5. 检索操作（Retrieve）
执行：

输入：预处理后的用户请求。
输出：top-k 最相关的 memory segments（按语义相似度排序）。
检索策略固定：由记忆数据结构内部实现（MPNet/BM25），外部不可干预。
✅ 符合“不允许由外部决定如何检索”的要求。

6. 检索后操作（Post-Retrieve Operation）
职责：

对检索结果进行后处理：如重排序、过滤、拼接成 prompt。
允许多次查询记忆数据结构（例如为补全上下文，再查相关 segments）。
文中体现：

检索到的 segments 直接拼接为上下文 prompt 输入 LLM（如 GPT-3.5-Turbo 或 Mistral-7B）。
虽未显式多次查询，但理论上允许（例如若首检结果不完整，可基于其中实体二次检索）。
在 human evaluation 中，“Memorability” 和 “Consistency” 得分高，说明检索后拼接有效保留了关键信息。
