# PreInsert 算子与数据结构兼容性 & Pipeline 替换可行性

> 说明：本表仅从“技术可组合性（是否能运行）”角度给出 ✓/×，不代表性能优劣。若有边界/注意事项，使用脚注标注。
>
> 三类 PreInsert 大类：none（无处理）、transform（结构变换）、extract（语义抽取）。

---

## A. 三类 PreInsert 算子 × 数据结构兼容性（精简版）

仅区分两类数据结构，不再细分到具体子结构；若某些细分类存在必须打叉的情况，见表后说明。

| 数据结构类别 | none | transform | extract |
| --- | --- | --- | --- |
| Partitional | ✓ | ✓ | ✓ |
| Hierarchical | ✓ | ✓ | ✓ |

不兼容细分说明（需打叉）：

- Hierarchical - 图型结构（Property Graph / Lnknote Graph / SIKG）：以下抽取算子不兼容图关系构建或会导致图索引失效 → ×：
	- `extract.keyword`
	- `extract.fact`
	说明：上述产物无法直接映射为“实体/关系”，建议改用 `extract.entity` 或 `extract.triple`。

---

## B. 细分 PreInsert 算子 × Pipeline 替换可行性（MemoryOS / TiM / Mem0ᵍ）

参考配置路径：`sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/primitive_memory_model`
- TiM：`locomo_tim_pipeline.yaml`（当前 `pre_insert: extract.triple`）
- MemoryOS：`locomo_memoryos_pipeline.yaml`（当前 `pre_insert: none`）
- Mem0ᵍ：`locomo_mem0g_pipeline.yaml`（当前 `pre_insert: extract.triple`）

说明：✓ 表示技术上可替换并能正常运行；× 表示不建议/可能破坏核心索引能力（尤其图层），或语义产物与预期结构严重不匹配。

| 类别 | 细分算子 | TiM | MemoryOS | Mem0ᵍ |
| --- | --- | --- | --- | --- |
| none | none | ✓ | ✓ | ✓ |
| transform | segment_denoise | ✓ | ✓ | ✓² |
| transform | summarize | ✓ | ✓ | ✓² |
| extract | keyword | ✓ | ✓ | ×³ |
| extract | entity | ✓ | ✓ | ✓ |
| extract | triple | ✓ | ✓ | ✓ |
| extract | fact | ✓ | ✓ | ×³ |

注释：
- ² Mem0ᵍ 包含语义与倒排层，transform 仍可运行，但若仅 transform 而不做关系抽取，图层收益会下降。
- ³ 图版（Mem0ᵍ）核心依赖实体/关系/三元组以构图；`keyword/noun/multi_summary/fact` 等产物不直接映射为图关系，可能导致图索引空洞，故不建议（×）。

---

## 建议
- 图场景（PG/LG/SIKG）：优先使用 `extract.entity` 或 `extract.triple`，必要时在前置加入结构化变换以提升抽取质量。
