# PostRetrieval ��������ʵ�����

> �������������Լ�����ṹ��TiM, MemoryOS, Mem0g������� PostRetrieval �׶εĶԱ�ʵ��
>
> Ŀ�꣺�ڲ�ͬ������ܹ��£����������������Զ����մ�������Ӱ��
>
> ʵ�鷶Χ��PostRetrieval �׶Σ��̶������׶�Ϊ baseline ����

______________________________________________________________________

## ? PostRetrieval ���Է�����ϵ

��ʵ���������ͳһ�Ĳ��Է����׼����������𻮷֣�

| ���            | ��������               | ���ܶ�λ                               | ���ó���                                 |
| --------------- | ---------------------- | -------------------------------------- | ---------------------------------------- |
| **1. ����**     | `filter.top_k`         | ����ǰK����߷ֵļ�����Ŀ              | �������������������ĳ���                 |
|                 | `filter.threshold`     | ���ݷ�����ֵ���˵��������             | ������֤����������ؼ���                 |
|                 | `filter.token_budget`  | ����tokenԤ�����ƽ������              | LLM�����Ĵ�������                        |
| **2. ������**   | `rerank.semantic`      | �����������ƶ���������                 | ���������壨TiM�������������            |
|                 | `rerank.time_weighted` | ����ʱ��Ȩ����������                   | ʱ�����г�����ǿ���½�����               |
|                 | `rerank.weighted`      | �����Ӽ�Ȩ������                       | �ۺϿ������ƶȡ�ʱ��ȶ������           |
|                 | `rerank.ppr`           | PageRank���Ի�������                   | ͼ�����壬�������ӹ�ϵ                   |
| **3. �ϲ�**     | `merge.multi_query`    | ִ�ж����ѯ���ϲ����                 | ��ǿ�ٻأ����ӽǼ�����MemGPT��           |
|                 | `merge.multi_tier`     | �ϲ����������                       | ��λ����䣨MemoryOS��                   |
|                 | `merge.link_expand`    | ��չ���ӹ�ϵ��������ؼ���             | ͼ�����壬���ýṹ��Ϣ                   |
|                 | `merge.scm_three_way`  | SCM��·�ϲ�                            | SCM�ض�����                              |
| **4. ��ǿ**     | `augment`              | ����persona/traits/summary��������     | ��ǿ����ɶ��ԣ����Ի���Ϣ����           |
|                 | `augment.reinforce`    | ���±����������ǿ�Ⱥ�ʱ���           | MemoryBank�������ߣ�����ǿ��             |
| **5. �޴���**   | `none`                 | ֱ��ʹ��ԭʼ�����������������       | Baseline�Ա�                             |

**�������ԭ��**��

- **��������**��ÿ������ܶ������߽�����
- **������**����ͬ�������䲻ͬ������ܹ�
- **ʵ���Ѻ�**���ɰ������ƶԱ�ʵ�����

______________________________________________________________________

## ? ʵ����Ʒ���

### �̶���������

ѡ�����������Լ�����ṹ��ʹ����ԭʼ���ã�

| ������      | �����ļ�                                      | �ܹ��ص�                         |
| ----------- | --------------------------------------------- | -------------------------------- |
| **TiM**     | `locomo_tim_pipeline.yaml`                    | ������ϣ���䣬������������       |
| **MemoryOS** | `locomo_memoryos_pipeline.yaml`               | ��λ����䣬����ṹ             |
| **Mem0g**   | `locomo_mem0g_pipeline.yaml`                  | ���嵹��֪ʶͼ�ף�ͼ+�������    |

### PostRetrieval �������

���ĸ������и�ѡһ�������Բ��������� `none` ��Ϊbaseline��

| ����        | ѡ�����              | ����                                   |
| ----------- | --------------------- | -------------------------------------- |
| **Filter**  | `filter.top_k`        | ��õĹ��˷��������ƽ������         |
| **Rerank**  | `rerank.semantic`     | �����������������������䣬ͨ����ǿ   |
| **Merge**   | `merge.multi_query`   | ���ѯ�ϲ�������RAG��ǿ����            |
| **Augment** | `augment`             | ������������Ϣ��persona/traits������ǿ����ɶ��� |
| **None**    | `none`                | ������������Ϊbaseline               |

### ʵ�����

**�ܼƣ�3 �������� �� 5 ������ = 15 ��ʵ��**

| ������   | None | Filter.TopK | Rerank.Semantic | Merge.MultiQuery | Augment.Reinforce |
| -------- | ---- | ----------- | --------------- | ---------------- | ----------------- |
| TiM      | ?    | ?           | ?               | ?                | ?                 |
| MemoryOS | ?    | ?           | ?               | ?                | ?                 |
| Mem0g    | ?    | ?           | ?               | ?                | ?                 |

______________________________________________________________________

## ? �����ļ������淶

```
{������}_{���ݼ�}_{����}_{�׶�}_pipeline.yaml
```

ʾ����
- `TiM_locomo_none_post_retrieval_pipeline.yaml`
- `TiM_locomo_top_k_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_semantic_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_multi_query_post_retrieval_pipeline.yaml`

______________________________________________________________________

## ?? ����ģ��ṹ

ÿ�������ļ��������¹ؼ����֣�

```yaml
# ============================================================
# PostRetrieval ʵ��: {������} + {����}
# ������ṹ: {����������}
# PostRetrieval ����: {��������}
# ��������: {�ļ���}
# ============================================================

runtime:
  dataset: locomo
  memory_name: "{������}-{����}"
  # ... ��������ʱ���ô�ԭʼ���ü̳�

services:
  # ��ԭʼ���������������̳�
  services_type: "..."
  # ...

operators:
  # ��ԭʼ���ü̳� pre_insert, post_insert, pre_retrieval
  # ���޸� post_retrieval ����

  post_retrieval:
    action: "{���Զ���}"
    # �����ض�����
    # ...
```

______________________________________________________________________

## ? ʵ������ָ��

### ��Ҫָ��

1. **������**
   - ׼ȷ�ʣ�Accuracy��
   - F1 ����
   - ROUGE/BLEU������������

2. **Ч��ָ��**
   - ����������ʱ
   - ����������Token����
   - �˵�����Ӧʱ��

3. **��������**
   - ��ؼ����ٻ���
   - ƽ������Է���
   - �����������

### ����ά��

- **���ԶԱ�**��ͬһ�������£���ͬ���Ե�Ч���Ա�
- **������Ա�**��ͬһ�����£���ͬ�������������
- **�ۺ϶Ա�**��15��ʵ���������־���

______________________________________________________________________

## ? ʵ��ִ������

1. **׼���׶�**
   - ȷ�������������������ÿ���������
   - ��֤ PostRetrieval �����Ե�ʵ��������

2. **��������**
   - ����ԭʼ���ã�����15��ʵ�������ļ�
   - ȷ��ֻ�޸� `post_retrieval` ���֣���������һ��

3. **ʵ��ִ��**
   - ������˳����������ʵ��
   - ��¼��ָ������

4. **�������**
   - ���ɶԱȱ���
   - �������������Ժ�Ч��

______________________________________________________________________

## ? ע������

1. **����������**��
   - `rerank.semantic` ��Ҫ embedding ֧��
   - `merge.multi_query` ��Ҫ LLM ���ɲ�ѯ��д
   - `augment` ��Ҫ������֧�� persona/traits ��ȡ�ӿ�

2. **��������**��
   - `top_k`: ���� 5-20
   - `num_queries`: ���� 2-5
   - `augment_type`: persona/traits/summary/metadata
   - `position`: before/after/both

3. **�Աȹ�ƽ��**��
   - �̶���ͬ�� LLM��Embedding ģ��
   - �̶���ͬ�����ݼ��Ͳ��Է�Ƭ
   - ���仯 PostRetrieval ����

______________________________________________________________________

## ? �����ļ��嵥

### TiM (5������)
- `TiM_locomo_none_post_retrieval_pipeline.yaml`
- `TiM_locomo_top_k_post_retrieval_pipeline.yaml`
- `TiM_locomo_semantic_post_retrieval_pipeline.yaml`
- `TiM_locomo_multi_query_post_retrieval_pipeline.yaml`
- `TiM_locomo_augment_post_retrieval_pipeline.yaml`

### MemoryOS (5������)
- `MemoryOS_locomo_none_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_top_k_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_semantic_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_multi_query_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_augment_post_retrieval_pipeline.yaml`

### Mem0g (5������)
- `Mem0g_locomo_none_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_top_k_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_semantic_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_multi_query_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_augment_post_retrieval_pipeline.yaml`

______________________________________________________________________

## ? ���ٿ�ʼ

```bash
# ���е���ʵ��
python main.py --config benchmarks/experiment/config/context_integration_mechanism/TiM_locomo_none_post_retrieval_pipeline.yaml

# ������������ʵ��
for config in benchmarks/experiment/config/context_integration_mechanism/*.yaml; do
    python main.py --config "$config"
done
```

______________________________________________________________________

*ʵ��������ڣ�2026��1��13��*
