# KG04 证据规范V9清洗同义词与导出Schema图谱 上传版

## 用途
用于证据等级、规则占位、规范版本占位、V9清洗审计、评分同义词路由和机器可读表结构。它保证知识图谱可审计、可扩展、可检索、可导出。

## 证据等级
| 等级 | 适用 | 要求 | 冲突优先级 |
|---|---|---|---|
| A_primary | 招标文件、答疑、合同、图纸、清单、评分办法、平台规则、正式规范 | source、page、clause、original_text/evidence | 最高 |
| A_secondary | 行业经验、常见评分项、通用措施、专家关注点、V9清洗能力 | 不得覆盖正式文件 | 低于A_primary |
| A_pending | 未上传的评分、暗标、页数、格式、签章、平台、AI规则 | source_required=true、input_required、upgrade_condition | 等待升级 |

## 关键词增强分类Schema
| 类别 | 字段名 | 典型关键词 | 证据要求 |
|---|---|---|---|
| 评分关键词 | scoring_keywords | 评分项原文、高档词、科学合理、完整、针对性、可实施、可检查、可追溯 | 来源于评标办法，保留页码、条款或原文 |
| 行业关键词 | industry_keywords | 公路工程、路基、路面、桥涵、隧道、交安机电、保通迁改、试验检测、交工验收 | 来源于图纸、清单、合同范围或评分项 |
| 工艺关键词 | process_keywords | 试验段、分层填筑、压实检测、配合比、拌运摊碾、张拉压浆、单机调试、系统联调 | 来源于专业节点或专项方案 |
| 重难点关键词 | difficulty_keywords | 软基沉降、台背回填、温度离析、边坡水害、接口协议、交通导改、雨季施工 | 需绑定工程对象和风险原因 |
| 风险关键词 | risk_keywords | R2、R3、暗标、否决项、证据不足、无依据强结论、完成态承诺、行业不匹配 | 需绑定整改卡和复检状态 |
| 质量控制关键词 | quality_keywords | 控制目标、质量标准、检查频次、检测方法、隐蔽验收、交工检测、整改复核 | 需有标准来源或A_pending占位 |
| 安全控制关键词 | safety_keywords | 危险源、危大工程、专项方案、安全交底、巡查记录、应急处置、文明施工 | 需有安全制度、专项方案或检查记录 |
| 绿色施工关键词 | green_keywords | 扬尘、噪声、污水、弃方、RAP再生、节材降碳、水保、环保台账 | 需有环保要求、台账或影像资料 |
| 智慧建造关键词 | smart_keywords | BIM、智慧工地、4D进度、视频巡检、预警复核、人工复核、碳台账 | 需有数据来源、复核机制和验收资料 |
| 验收关键词 | acceptance_keywords | 旁站记录、检测报告、隐蔽验收、实体检测、验收表、缺陷整改、移交 | 需有真实记录或“需补充”占位 |
| 证据留痕关键词 | trace_keywords | source、page、clause、影像资料、台账、审批文件、调试记录、联调报告 | 用于高权重识别和审计追溯 |

## 关键词权重导出规则
| 字段 | 取值 | 说明 |
|---|---|---|
| keyword_position | title/scoring/process/standard/acceptance/evidence/description | 标题、评分点、工艺、标准、验收、证据、普通描述 |
| keyword_weight | high/medium_high/medium/low | 标题、评分点、证据留痕为high；工艺和验收为medium_high；普通描述为low |
| keyword_density_status | balanced/sparse/stacked/mismatched | balanced为自然分布；stacked为堆砌；mismatched为行业不匹配 |
| evidence_binding | A_primary/A_secondary/A_pending/none | 无证据时不得写强结论 |
| ai_recognition_note | 可抽取原因 | 说明关键词如何支撑评分项、对象、措施、验收和证据 |

## 项目级关键词覆盖矩阵Schema
| 字段 | 要求 |
|---|---|
| keyword | 关键词原文，保留项目名称、评分项、清单子目、图纸参数和答疑澄清表述 |
| keyword_category | project_base/scoring/engineering_object/process/material_parameter/risk_control/acceptance/clarification_override/low_value_phrase |
| source_file | 来源文件名，不得为空 |
| source_ref | 来源页码、条款号或行号；缺页码时用可复核的行号占位 |
| engineering_part | 对应工程部位、清单子目、图纸构造或项目范围 |
| chapter | 对应施组章节S-01至S-17 |
| recommended_usage | 推荐写入方式，说明标题、段首、表格列、验收或留痕位置 |
| weight | 最高权重/高权重/中高权重/普通权重/低权重/剔除 |
| risk_level | R0/R1/R2/R3，说明漏写、错写或旧内容残留风险 |
| is_scoring_keyword | true/false，评分项和扣分项必须为true |
| is_clarification_override | true/false，答疑澄清、补遗变更覆盖原内容时为true |
| must_appear_in_technical_bid | true/false，最高权重、高权重和评分关键词通常为true |
| suggested_frequency | 建议出现频次，按权重和章节需要控制，防止堆砌 |
| trace_evidence | 可关联检测、验收、留痕资料，如检测报告、隐蔽验收、影像资料、台账 |

## 动态增强验收规则
项目资料包生成矩阵后必须验证：能自动生成项目级关键词覆盖矩阵；评分项标记高权重或最高权重；答疑澄清覆盖旧关键词；清单主要子目进入工程对象关键词；图纸材料、结构、参数进入材料与参数关键词；施组章节能够调用项目关键词；空泛通用词不提升为高权重；每个关键词可追溯来源文件和页码/条款/行号；不影响既有知识图谱、项目分类、施组生成和审查评分功能；不得输出.env、Token、Cookie、Authorization、AppSecret、SSH key、数据库、日志或缓存文件。

## 规则占位
必须为以下规则保留占位：评分标准、暗标、页数、字体字号、目录页眉页脚、电子投标上传、签章盖章、雷达检测、AI自动评审、地方公共资源交易规则、专业特殊要求、废标条款、响应性评审、资格审查、技术标否决项。未取得正式文件前，不得虚构具体规则。

## 技术标准校核与规范版本占位
不得凭记忆写死标准编号、年份和条文。编制具体施工方案时，先读取项目资料中的技术标准、图纸说明、招标技术要求和合同条款；项目资料已明确参数的，以项目资料为准；未明确但确需补充的，再调用知识库内现行有效规范；具备联网能力时，应检索官方或权威来源确认最新有效标准。无法确认来源的参数不得编造，应写“按设计文件及现行规范要求执行”，并标记“需核实”。不得虚构厚度、强度、间距、坡度、材料型号、检测频次、验收数值。

公路、房建厂房、市政道路、水利水电、管网、园林绿化、高标准农田等行业规范版本均需由招标文件、规范清单或用户资料确认。缺版本时写：该项标准版本需结合招标文件/规范清单补充后方可细化。

## V9清洗规则
| 原生风险 | 清洗动作 | 允许表达 |
|---|---|---|
| 品牌/身份触发词 | 删除 | 按工程对象、评分项和证据触发 |
| 原生营销式分档 | 删除 | 只保留可验证措施和记录 |
| 固定加分、Top百分比 | 删除 | 支撑评分完整性、针对性、可追溯性 |
| 竞品压制 | 删除 | 客观技术风险和本项目控制措施 |
| 零事故、零盲区、一次成功、固定达标 | 降级 | 拟设置、形成记录、经检测验收确认 |
| 自动停机、自动评分、自动派单闭环 | 降级 | 报警提示、人工复核、审批处置 |
| 固定节能、工期收益、金融收益 | 删除或待测算 | 根据台账、计量、核算确认 |
| 已接入、已投运、已验收 | 缺记录时降级 | 拟接入、需补充联调验收记录 |
| 非公路行业主体工艺 | 隔离 | 只作接口、迁改、保护、审批边界 |

## V9可用方向
RAP厂拌热再生可用于绿色低碳和路面质量控制，但必须有RAP来源、配合比、计量和抽检。DAS、OTDR、智能感知可用于智慧公路和通信接口，但必须有光缆资源、设备表、接口协议、联调和验收。BIM、智慧工地、4D进度、绿色碳台账、安全识别、关键链进度可作为条件性措施，不得写完成态或固定收益。

## 同义词路由
| 用户表达 | 归一评分意图 | 路由 |
|---|---|---|
| 施工部署、组织安排、总体策划 | 施工组织合理性 | S-03/S-05 |
| 特点难点、重难点、针对性 | 项目理解与重难点 | S-02 |
| 土石方、填挖方、特殊路基 | 路基施工 | S-06 |
| 沥青、水稳、基层、面层、RAP | 路面施工 | S-07 |
| 边坡、水害、截排水 | 排水防护 | S-08 |
| 桥梁、涵洞、张拉、桩基 | 桥涵专项 | S-09 |
| 标志标线、护栏、照明、监控 | 交安机电 | S-11 |
| 保通、导改、交通组织 | 施工交通 | S-12 |
| 质量、试验、检测、验收 | 质量保证 | S-13 |
| 安全、危大、文明施工 | 安全文明 | S-14 |
| 扬尘、噪声、水保、绿色 | 环保绿色 | S-15 |
| BIM、智慧工地、数字化、四新 | 智慧创新 | S-16 |
| 移交、养护、竣工资料 | 交付管护 | S-17 |

## 扩展同义词与评标表达路由
| 表达簇 | 归一字段 | 适用章节 |
|---|---|---|
| 科学合理、先进可行、组织严密、针对性强、完整详实 | scoring_keywords | S-01/S-03/S-05 |
| 关键线路、节点工期、资源保障、纠偏措施、动态优化 | process_keywords | S-05 |
| 控制目标、关键工序、质量标准、检查频次、责任主体 | quality_keywords | S-06/S-07/S-09/S-13 |
| 验收方法、检测报告、旁站记录、隐蔽验收、影像资料 | acceptance_keywords/trace_keywords | S-13/S-17 |
| 风险闭环、整改通知、整改复核、复检确认、闭环销项 | risk_keywords | S-03/S-13/S-14 |
| 安全交底、危大清单、专项方案、巡查记录、应急处置 | safety_keywords | S-14 |
| 扬尘治理、噪声控制、污水处理、弃方管理、水保恢复 | green_keywords | S-15 |
| BIM模型、智慧工地、视频巡检、预警复核、人工确认 | smart_keywords | S-16 |
| 单机调试、系统联调、接口测试、验收移交、联调报告 | process_keywords/acceptance_keywords | S-11 |
| 保通审批、导改布设、交通疏解、巡查保畅、恢复移交 | safety_keywords/trace_keywords | S-12 |

## 行业匹配过滤规则
关键词必须与项目行业、工程类别、施工内容、评标场景和技术要求匹配。未被图纸、清单、合同范围或评分项激活的专业内容只能作为条件性节点，不得写成本项目事实。发现其他行业主体工艺、其他项目名称或模板残留时，按“隔离—删除—改为接口/保护/协调边界—需补充资料”处理；不得为提高词频强行加入无关行业词。

行业差异必须保留：房建厂房关注主体结构、屋面防水、装饰装修、机电安装、消防联动、室外配套；市政道路关注路基、基层、面层、排水、交通组织、管线保护；水利水电关注堤防、护岸、防渗墙、导流、度汛、水保环保、单元工程验收；管网工程关注沟槽、支护、降排水、管道安装、闭水试验、回填压实、井室施工；园林绿化关注土壤改良、苗木栽植、养护、灌溉、成活率、景观恢复；高标准农田关注土地平整、灌排沟渠、田间道路、涵闸、泵站、农田防护。

## 导出Schema
| 文件 | 字段 |
|---|---|
| nodes.csv | node_id,node_name,node_type,domain,evidence_level,priority,keywords,synonyms,description,source,page,clause,mapped_chapters,risk_if_missing,verification_points,update_status |
| edges.csv | edge_id,source_node_id,target_node_id,relation_type,relation_description,evidence_level,weight,condition,conflict_rule,update_status |
| keyword_enhancement.csv | keyword_id,linked_node_id,keyword_category,keyword_text,synonym_group,keyword_position,keyword_weight,evidence_binding,ai_recognition_note,density_status,industry_match_status |
| project_keyword_coverage_matrix.csv | keyword,keyword_category,source_file,source_ref,engineering_part,chapter,recommended_usage,weight,risk_level,is_scoring_keyword,is_clarification_override,must_appear_in_technical_bid,suggested_frequency,trace_evidence |
| keyword_weight_rules.csv | position,weight_level,trigger_condition,required_evidence,demotion_condition,review_action |
| project_score_matrix.csv | score_id,source_doc_id,page,clause,original_text,points_or_grade,high_grade_terms,extracted_keywords,keyword_weight_map,mapped_chapters,project_objects,required_response,evidence_required,evidence_trace_keywords,blocker,release_status |
| simulation_review.csv | review_id,linked_score_id,chapter,risk_level,problem,cause,weak_keyword_category,remedy_action,verification_point,closure_status |
| remedy_cards.csv | remedy_id,linked_score_id,risk_level,problem,cause,affected_chapter,weak_keyword_position,rewrite_action,rewritten_sentence,evidence_trace_required,verification_point,closure_status |
| final_release_checklist.csv | gate,check_result,evidence_or_rule,open_issue,release_judgement |

## 上传前QA
检查项：只上传最终Knowledge和系统指令；无本机路径；无原生触发词、固定加分、竞品压制；无“完成态”无证表达；无重复节点ID；所有A_pending有source_required、input_required和升级条件；系统指令字数不超过8000字；Knowledge与Instructions分离。
