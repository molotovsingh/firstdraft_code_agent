# Architecture Decision Records (ADR)
# FirstDraft v2.0 Legal AI Platform

This file documents significant architectural decisions made during the development of FirstDraft v2.0. Each decision is recorded with context, alternatives considered, and consequences to maintain institutional knowledge as the project evolves.

## ADR Template
```
## ADR-XXXX: [Decision Title]
**Date:** YYYY-MM-DD  
**Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-XXXX]  
**Context:** What problem are we solving?  
**Decision:** What we decided to do  
**Alternatives Considered:** What other options were evaluated  
**Consequences:** Benefits and drawbacks of this decision  
**Related ADRs:** Links to related decisions  
```

---

## ADR-0001: Modular "Lego Blocks" Architecture
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** FirstDraft v2.0 needs to be enterprise-scale (100+ customers, 1000+ docs/hour) while remaining maintainable and allowing independent development of different capabilities. Legacy v1-v9 system became monolithic and difficult to scale.

**Decision:** Implement 7 independent, world-class "Lego Blocks" that can be developed, deployed, and scaled independently:
0. **Block 0**: Document Pre-processing (OCR, quality assessment, format standardization)
1. **Block 1**: Entity Discovery Engine (SOTA AI + validation)
2. **Block 2**: Content Storage Engine (content-addressable + deduplication)  
3. **Block 3**: AI Processing Engine (multi-level AI cascade)
4. **Block 4**: Queue Management Engine (enterprise job orchestration)
5. **Block 5**: Multi-Tenant Management (client lifecycle + isolation)
6. **Block 6**: API Gateway Engine (external interface + routing)

**Alternatives Considered:**
- **Monolithic Architecture**: Simpler to start but doesn't scale to enterprise requirements
- **Traditional Microservices**: More granular but increases complexity without clear business value
- **Service Mesh Architecture**: Over-engineered for current scale, adds unnecessary complexity

**Consequences:**
- ✅ **Benefits**: Independent development cycles, targeted scaling, clean interfaces, easier testing
- ✅ **Benefits**: Each block can use optimal technology stack for its purpose
- ✅ **Benefits**: Enterprise customers can adopt blocks incrementally
- ⚠️ **Drawbacks**: More complex deployment coordination, inter-service communication overhead
- ⚠️ **Drawbacks**: Requires careful interface design between blocks

**Related ADRs:** ADR-0002 (Technology Stack), ADR-0003 (Block 0 First)

---

## ADR-0002: Technology Stack Selection
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Need modern, high-performance technology stack that supports async operations, enterprise scale, and developer productivity. Must handle 1000+ concurrent users and 1000+ documents/hour.

**Decision:** Standardize on modern Python ecosystem with enterprise-grade supporting services:
- **API Framework**: FastAPI (async, high performance, excellent typing)
- **Database**: PostgreSQL (ACID compliance, multi-tenant support, JSON capabilities)
- **Message Queue**: Redis/Celery (proven at scale, low latency)
- **AI Integration**: OpenRouter (multi-model access) + direct provider APIs
- **Containerization**: Docker + Kubernetes (industry standard)
- **Storage**: S3/MinIO (content-addressable, enterprise scale)
- **Package Manager**: UV (10-100x faster than pip)

**Alternatives Considered:**
- **Node.js/TypeScript**: Good performance but Python ecosystem better for AI/ML
- **Go/Rust**: Excellent performance but smaller talent pool and fewer AI libraries
- **Java/Spring**: Enterprise-proven but heavyweight, slower development cycles
- **MongoDB**: Document-focused but PostgreSQL JSON features provide best of both worlds

**Consequences:**
- ✅ **Benefits**: Modern async capabilities, excellent AI/ML ecosystem, strong typing
- ✅ **Benefits**: Enterprise-grade reliability and scalability
- ✅ **Benefits**: Large developer talent pool familiar with stack
- ⚠️ **Drawbacks**: Python GIL limitations (mitigated by async/multiprocessing)
- ⚠️ **Drawbacks**: Memory usage higher than compiled languages

**Related ADRs:** ADR-0001 (Lego Blocks), ADR-0004 (Multi-Tenant Database)

---

## ADR-0003: Block 0 Document Pre-processing First Implementation Strategy
**Date:** 2025-09-07  
**Status:** Accepted (Updated from Entity Discovery First)  
**Context:** Indian legal market reality requires robust document quality handling before any AI processing. Poor quality documents (photos, scanned images, mixed languages) are common due to diverse client education/income levels. Entity discovery cannot be effective without clean, standardized input.

**Decision:** Implement Block 0 (Document Pre-processing) first as the foundational layer, followed by Block 1 (Entity Discovery). All downstream blocks depend on clean, quality-assessed document inputs from Block 0.

**Key Features of Block 0:**
- OCR and format standardization for all document types
- Quality assessment and warning system (never reject)
- Image enhancement and rotation correction
- Multi-language support (Hindi/English mixed documents)
- Extensible schema for iterative enhancement

**Integration with Block 1:**
- Clean, standardized inputs enable effective entity discovery
- Quality warnings inform confidence scoring
- Document metadata enhances disambiguation context

**Alternatives Considered:**
- **Entity Discovery First**: Would fail due to poor document quality in Indian market
- **Content Storage First**: Foundational but cannot store unusable document formats
- **Parallel Development**: Higher risk of integration failures between preprocessing and AI
- **Third-party OCR Services**: Vendor dependency and cost concerns for high-volume processing

**Consequences:**
- ✅ **Benefits**: Handles Indian market document quality reality from day one
- ✅ **Benefits**: All subsequent blocks receive clean, standardized inputs
- ✅ **Benefits**: Quality warnings build user trust and set proper expectations
- ✅ **Benefits**: Extensible architecture allows iterative enhancement
- ⚠️ **Drawbacks**: Additional complexity before core legal AI value
- ⚠️ **Drawbacks**: Higher upfront development investment in infrastructure

**Related ADRs:** ADR-0001 (Lego Blocks), ADR-0005 (AI Model Strategy), ADR-0009 (Never Reject Strategy)

---

## ADR-0004: Multi-Tenant Database Isolation Strategy
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Enterprise legal clients require absolute data isolation for confidentiality and compliance. Single shared database creates security risks and limits per-client customization.

**Decision:** Implement database-per-tenant isolation with dedicated PostgreSQL databases for each enterprise client:
```
firstdraft_system (master tenant registry)
firstdraft_tenant_001 (enterprise client 1)
firstdraft_tenant_002 (enterprise client 2)  
firstdraft_tenant_xxx (per-tenant isolation)
```

**Security Features:**
- Complete data separation between tenants
- Tenant-specific encryption keys
- Independent backup and recovery per tenant
- Custom schema modifications per tenant if needed

**Alternatives Considered:**
- **Row-Level Security (RLS)**: Single database with tenant_id filtering - simpler but security risk if misconfigured
- **Schema-per-Tenant**: Multiple schemas in single database - middle ground but still shares database resources
- **Application-Level Filtering**: Relies on application code for isolation - highest security risk

**Consequences:**
- ✅ **Benefits**: Maximum security and compliance for legal industry
- ✅ **Benefits**: Independent scaling per tenant
- ✅ **Benefits**: Easier client onboarding/offboarding
- ✅ **Benefits**: Custom tenant configurations possible
- ⚠️ **Drawbacks**: Higher operational complexity
- ⚠️ **Drawbacks**: More resource usage per tenant
- ⚠️ **Drawbacks**: Cross-tenant analytics more complex

**Related ADRs:** ADR-0002 (Technology Stack), ADR-0006 (Secrets Management)

---

## ADR-0005: Premium AI Model Investment Strategy  
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Legal AI requires highest quality reasoning for entity discovery and document processing. Cost optimization through smart model selection and upstream processing quality.

**Decision:** Invest in premium AI models (Claude-3.5-Sonnet, GPT-4o) for core reasoning tasks while using cost-effective models for simpler operations:
- **Premium Models**: Complex entity discovery, legal reasoning, multi-party relationship mapping
- **Cost-Effective Models**: Text classification, simple extraction, summarization
- **Multi-Model Cascade**: Start with fast/cheap models, escalate to premium for complex cases

**AI Provider Strategy:**
- **Primary Gateway**: OpenRouter (unified API, model flexibility)
- **Direct Integration**: Anthropic, OpenAI for premium models
- **Cost-Effective**: DeepSeek, Together AI for high-volume simple tasks

**Alternatives Considered:**
- **Cost-First Strategy**: Use cheapest models available - risks quality for legal use cases
- **Single Provider**: Lock into one AI provider - limits flexibility and creates vendor dependency
- **Open Source Only**: Self-hosted models - reduces costs but increases infrastructure complexity

**Consequences:**
- ✅ **Benefits**: Highest quality results for complex legal reasoning
- ✅ **Benefits**: Cost optimization through intelligent model selection
- ✅ **Benefits**: Vendor flexibility and risk mitigation
- ✅ **Benefits**: Upstream quality investment reduces downstream costs
- ⚠️ **Drawbacks**: Higher initial costs for premium models
- ⚠️ **Drawbacks**: Complexity of managing multiple AI providers
- ⚠️ **Drawbacks**: Need sophisticated routing and fallback logic

**Related ADRs:** ADR-0003 (Block 0 First), ADR-0006 (Secrets Management)

---

## ADR-0006: Tiered Secrets Management Architecture
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Project requires 15+ different API keys and secrets across AI providers, databases, and infrastructure. Enterprise legal clients demand highest security standards. Security breach could be catastrophic.

**Decision:** Implement 4-phase tiered secrets management strategy:
1. **Phase 1**: Local .env files for development (never committed)
2. **Phase 2**: Cloud secrets manager (AWS/GCP/Azure) for staging/production
3. **Phase 3**: Container secrets injection for Docker deployments
4. **Phase 4**: Kubernetes secrets for production orchestration

**Multi-Tenant Secret Isolation:**
- Unique database passwords per tenant
- Separate encryption keys per tenant  
- Tenant-specific API quotas and monitoring
- Complete secret isolation between clients

**Alternatives Considered:**
- **Environment Variables Only**: Simple but insecure for production
- **Config Files**: Easy to accidentally commit secrets to git
- **HashiCorp Vault**: Excellent but adds significant operational complexity
- **Single Cloud Provider**: Vendor lock-in and single point of failure

**Consequences:**
- ✅ **Benefits**: Enterprise-grade security for legal industry
- ✅ **Benefits**: Multi-cloud flexibility
- ✅ **Benefits**: Development to production consistency
- ✅ **Benefits**: Automated secret rotation capabilities
- ⚠️ **Drawbacks**: Complex setup and management
- ⚠️ **Drawbacks**: Multiple systems to secure and monitor
- ⚠️ **Drawbacks**: Higher operational overhead

**Related ADRs:** ADR-0004 (Multi-Tenant Database), ADR-0005 (AI Model Strategy)

---

## ADR-0007: UV Package Management Adoption
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Python dependency management is traditionally slow with pip. Project inherits UV usage from parent v1-v9 system. Need fast, reliable dependency resolution for 6-block architecture.

**Decision:** Standardize on UV package manager across all blocks:
- 10-100x faster dependency resolution than pip
- Modern lockfile support for reproducible builds
- Excellent virtual environment management
- Compatible with existing pip/PyPI ecosystem

**Development Workflow:**
```bash
uv add fastapi uvicorn anthropic openai    # Add dependencies
uv add --dev pytest black flake8          # Add dev dependencies  
uv sync                                    # Install all dependencies
uv run python main.py                     # Run in UV environment
```

**Alternatives Considered:**
- **Traditional pip**: Familiar but slow, no lockfiles
- **Poetry**: Good dependency management but slower than UV
- **Pipenv**: Deprecated and slower than UV
- **Conda**: Great for data science but overkill for this project

**Consequences:**
- ✅ **Benefits**: Dramatically faster dependency resolution and installation
- ✅ **Benefits**: Reproducible builds with lockfiles
- ✅ **Benefits**: Modern tooling aligned with Python ecosystem direction
- ✅ **Benefits**: Consistency with parent project tooling
- ⚠️ **Drawbacks**: Less mature than pip (though rapidly improving)
- ⚠️ **Drawbacks**: Team needs to learn new commands
- ⚠️ **Drawbacks**: Some edge cases may require pip fallback

**Related ADRs:** ADR-0002 (Technology Stack), ADR-0008 (Development Workflow)

---

## ADR-0008: Git Workflow and Branching Strategy
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** 6-block modular architecture requires coordinated but independent development. Need workflow that supports parallel block development while maintaining integration quality.

**Decision:** Implement block-specific branching strategy with integration coordination:

**Branch Structure:**
```
main (production-ready)
├── dev (integration branch)
├── block1/entity-discovery (Block 1 development)
├── block2/content-storage (Block 2 development)
├── block3/ai-processing (Block 3 development)
├── block4/queue-management (Block 4 development)
├── block5/multi-tenant (Block 5 development)
├── block6/api-gateway (Block 6 development)
├── feature/cross-block-integration (multi-block features)
└── release/v2.x.x (release preparation)
```

**Development Phases:**
- **Phase 1 (Week 1-2)**: Single block focus, minimal git complexity
- **Phase 2 (Week 3-6)**: Multi-block coordination with integration testing
- **Phase 3 (Week 8+)**: Full enterprise workflow with quality gates

**Alternatives Considered:**
- **GitFlow**: Too heavyweight for early development phase
- **GitHub Flow**: Too simple for coordinated multi-block releases
- **Trunk-Based Development**: Requires mature CI/CD not available yet
- **Feature Branches Only**: Doesn't organize block-specific development

**Consequences:**
- ✅ **Benefits**: Independent block development cycles
- ✅ **Benefits**: Clear coordination points for integration
- ✅ **Benefits**: Scales from simple to complex as project matures
- ✅ **Benefits**: Supports both individual and team development
- ⚠️ **Drawbacks**: More complex than simple feature branching
- ⚠️ **Drawbacks**: Requires discipline to maintain branch hygiene
- ⚠️ **Drawbacks**: Merge conflicts possible between blocks

**Related ADRs:** ADR-0001 (Lego Blocks), ADR-0003 (Block 0 First)

---

---

## ADR-0009: "Never Reject, Always Warn" Document Quality Strategy
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Indian legal market serves diverse client base with varying education/income levels. Clients often provide poor quality documents (photos of papers, blurry scans, handwritten notes). Rejecting documents creates user friction and doesn't reflect legal practice reality where lawyers must work with whatever evidence is available.

**Decision:** FirstDraft will never reject documents regardless of quality. Instead, implement comprehensive quality assessment and warning system:
- Process all documents with best-effort techniques
- Provide specific quality warnings per document
- Ask users if they can provide better versions
- Flag outputs with quality impact warnings
- Maintain processing pipeline integrity despite input quality

**Quality Assessment Approach:**
- Document readability scoring (text clarity, OCR confidence)
- Format standardization success rates
- Language detection and mixed-language handling
- Visual quality metrics (resolution, contrast, rotation)
- Content completeness assessment

**Alternatives Considered:**
- **Quality Gating**: Reject poor documents - creates user friction and doesn't match legal reality
- **Manual Review Queue**: Human intervention for poor quality - doesn't scale and defeats automation purpose
- **Tiered Processing**: Different workflows for quality levels - adds complexity without clear user benefit
- **Silent Processing**: No quality warnings - undermines user trust in outputs

**Consequences:**
- ✅ **Benefits**: Matches legal practice reality where all evidence must be considered
- ✅ **Benefits**: Eliminates user friction and rejection-based abandonment
- ✅ **Benefits**: Builds trust through transparency about processing limitations
- ✅ **Benefits**: Enables data collection on quality patterns for future improvements
- ⚠️ **Drawbacks**: More complex processing pipeline with error handling
- ⚠️ **Drawbacks**: Users may rely on poor-quality outputs without heeding warnings
- ⚠️ **Drawbacks**: Higher computational costs processing difficult documents

**Related ADRs:** ADR-0003 (Block 0 First), ADR-0010 (Credit-Based Architecture)

---

## ADR-0010: Credit-Based Architecture with Model Recommendation System
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Legal AI processing costs vary dramatically based on document complexity and AI model selection. Users need cost transparency and control, especially for budget-conscious Indian market. Business model directly affects technical architecture design.

**Decision:** Implement credit-based system with intelligent model recommendation and user override capabilities:

**Core Architecture:**
- Credit consumption tracking at granular task level
- Upfront cost estimation before processing
- Model recommendation engine based on task complexity
- Simple user override with revised cost estimates
- Real-time credit consumption monitoring

**User Experience Flow:**
1. Document analysis and complexity assessment
2. Model recommendation with cost estimate
3. User choice: Accept or override with budget models
4. Processing with real-time credit tracking
5. Final cost reconciliation and reporting

**Technical Requirements:**
- Database schema for credit tracking and model usage
- Cost estimation algorithms per AI provider/model
- Model routing and fallback systems
- Usage analytics and billing integration
- Credit management and purchasing workflows

**Alternatives Considered:**
- **Flat Subscription**: Simple but doesn't reflect actual usage costs
- **Pay-per-Document**: Too coarse-grained, doesn't account for complexity
- **Time-Based Billing**: Doesn't correlate with AI processing costs
- **Hidden Costs**: Better UX but reduces user trust and control

**Consequences:**
- ✅ **Benefits**: Cost transparency builds user trust and adoption
- ✅ **Benefits**: Users control cost/quality tradeoffs based on budget
- ✅ **Benefits**: Business model scales with actual AI processing costs
- ✅ **Benefits**: Usage data enables pricing optimization
- ⚠️ **Drawbacks**: Complex billing and credit management system required
- ⚠️ **Drawbacks**: Cost estimation accuracy affects user satisfaction
- ⚠️ **Drawbacks**: Model recommendation system needs sophisticated logic

**Related ADRs:** ADR-0005 (AI Model Strategy), ADR-0011 (Foundation-First Philosophy)

---

## ADR-0011: Foundation-First Development Philosophy  
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Legal AI market is crowded with tools promising advanced insights and legal advice. Many fail because they attempt sophisticated analysis on poor foundational data. Lawyers need reliable data extraction before insights. Positioning as "AI Paralegal" rather than lawyer replacement.

**Decision:** Implement foundation-first development philosophy across all blocks:

**MVP Scope - Foundation Data Layer:**
- Document organization and categorization
- Entity cataloging with confidence scores
- Timeline construction with source references
- Key document identification and classification
- Basic fact extraction (dates, amounts, claims)
- Conflict flagging with best-guess resolution

**Explicitly Excluded from MVP:**
- Legal advice or recommendations
- Privilege determinations
- Case strategy suggestions  
- Document quality scoring
- Opposing counsel analysis
- Jurisdiction-specific legal guidance
- Advanced analytics and insights

**Success Criteria:**
- Replace paralegal grunt work, not experienced lawyer judgment
- 90%+ accuracy on foundational data extraction
- Lawyer-level trust in outputs for case preparation
- Clear path to insights/advisory features post-MVP

**Alternatives Considered:**
- **Insights-First**: Attempt sophisticated legal analysis early - high failure risk
- **Full-Stack MVP**: Build all capabilities simultaneously - scope creep risk
- **AI-First**: Focus on impressive AI capabilities over data quality - trust risk
- **Feature Parity**: Match existing legal AI tools - commoditization risk

**Consequences:**
- ✅ **Benefits**: Clear value proposition that lawyers understand and trust
- ✅ **Benefits**: Achievable technical scope with measurable success metrics
- ✅ **Benefits**: Foundation data enables superior insights in future phases
- ✅ **Benefits**: Positions against over-promising AI tools in market
- ⚠️ **Drawbacks**: Less impressive demo than insight-heavy competitors
- ⚠️ **Drawbacks**: Longer path to high-value legal advisory features
- ⚠️ **Drawbacks**: May be perceived as "just another document processor"

**Related ADRs:** ADR-0003 (Block 0 First), ADR-0012 (Indian Market Optimization)

---

## ADR-0012: Indian Market Optimization Strategy
**Date:** 2025-09-07  
**Status:** Accepted  
**Context:** Indian legal market has unique characteristics: diverse client education/income levels, mixed document quality, Hindi/English language mixing, different legal procedures, and price sensitivity. Global legal AI tools often fail to address these specific challenges.

**Decision:** Design FirstDraft v2.0 specifically for Indian market realities:

**Document Quality Handling:**
- Robust OCR for photos and scanned documents
- Image enhancement and rotation correction
- Mixed-language document processing (Hindi/English)
- Quality assessment without rejection

**Pricing Strategy:**
- Credit-based model accommodates budget constraints
- Transparent cost control with override options
- Local currency pricing and payment methods
- Flexible scaling for solo practitioners to large firms

**Legal System Alignment:**
- Indian legal document formats and procedures
- Common entity types in Indian litigation
- Cultural context in entity disambiguation
- Regional language support expansion path

**Market Positioning:**
- "AI Paralegal" resonates with Indian legal hierarchy
- Cost savings focus vs. premium feature positioning
- Local case studies and testimonials
- Integration with existing Indian legal workflows

**Alternatives Considered:**
- **Global-First Design**: Build for US/EU markets then adapt - misses local nuances
- **Premium Positioning**: High-cost, high-value approach - excludes large market segment
- **English-Only**: Simpler but excludes significant user base
- **Western Legal System**: Assumes common law similarities - misses procedural differences

**Consequences:**
- ✅ **Benefits**: First-mover advantage in underserved Indian legal AI market
- ✅ **Benefits**: Product-market fit through deep local understanding
- ✅ **Benefits**: Competitive moat through India-specific optimizations
- ✅ **Benefits**: Scalable foundation for expansion to similar markets
- ⚠️ **Drawbacks**: Limits initial global expansion opportunities
- ⚠️ **Drawbacks**: India-specific features may not translate to other markets
- ⚠️ **Drawbacks**: Requires deep understanding of Indian legal system nuances

**Related ADRs:** ADR-0009 (Never Reject Strategy), ADR-0010 (Credit-Based Architecture)

---

## ADR-0013: User Management and Document Association Architecture
**Date:** 2025-09-09  
**Status:** Accepted  
**Context:** Block 0 document processing requires mapping documents to users for ownership, access control, and audit trails. Initial implementation used tenant_id as user_id, which doesn't scale to multi-user enterprise environments. Need simple user management that avoids future technical debt while supporting basic use cases.

**Decision:** Implement integer-based user-document relationships with minimal user management:

**User Management Design:**
- Users table with integer primary key (standard relational design)
- Tenant-scoped users (users belong to specific tenants)
- Simple user identification: Amit and Claude as initial test users
- Standard foreign key relationships: `documents.user_id → users.id`

**Database Schema:**
```sql
Users:
- id (integer PK) - efficient joins, standard approach
- tenant_id (UUID) - multi-tenant isolation 
- username (string) - human-readable identifier
- display_name (string) - UI presentation

Documents:
- user_id (integer FK) - replaces created_by UUID field
- Standard foreign key constraint to Users.id
```

**API Design:**
- Add user_id parameter to document upload endpoints
- Validate user belongs to specified tenant
- Default to user_id=1 (Amit) for backward compatibility

**Alternatives Considered:**
- **UUID-based user relationships**: More complex, slower joins, non-standard for user management
- **No user management**: Current state - unusable for multi-user environments  
- **Complex RBAC system**: Over-engineered for current test requirements
- **Username-only identification**: No referential integrity, harder to extend

**Consequences:**
- ✅ **Benefits**: Standard relational design with efficient integer foreign keys
- ✅ **Benefits**: Natural foundation for future role-based permissions
- ✅ **Benefits**: Simple to understand and implement
- ✅ **Benefits**: Minimal technical debt for enterprise scaling
- ✅ **Benefits**: Proper audit trail and document ownership tracking
- ⚠️ **Drawbacks**: Breaking change to existing document upload API
- ⚠️ **Drawbacks**: Requires data migration for existing documents
- ⚠️ **Drawbacks**: Additional validation logic in API layer

**Related ADRs:** ADR-0004 (Multi-Tenant Database), ADR-0014 (Database Schema Design)

---

## ADR-0014: Centralized LLM Service Architecture with Multi-Provider Fallback
**Date:** 2025-09-10  
**Status:** Accepted  
**Context:** All blocks (1-6) will require LLM integration for various tasks. Instead of hardcoding AI provider logic in each block, need centralized service with robust fallback architecture. OpenRouter provides model flexibility but requires fallback to direct providers for reliability. Credit estimation and usage tracking must be consistent across all blocks.

**Decision:** Implement shared LLM service module (`shared/llm_service/`) with multi-provider fallback chain:

**Fallback Architecture:**
```
OpenRouter Model 1 → OpenRouter Model 2 → Anthropic Direct → OpenAI Direct → Gemini Direct
```

**Core Components:**
- **LLMRouter**: Main interface with fallback logic and 2 retries per provider
- **Task-Specific Selection**: Different model preferences per task type (entity_discovery, classification, etc.)
- **Credit System**: Crude estimation method with database schema for future sophistication
- **Error Tracking**: Comprehensive logging for provider failures and recovery analytics
- **Configuration Management**: Simple, robust model preferences and fallback chains

**Technical Design:**
```python
# Any block usage pattern:
from shared.llm_service import LLMRouter

class AnyBlockEngine:
    def __init__(self):
        self.llm = LLMRouter()
    
    def process(self, content, user_context):
        return self.llm.complete(
            task_type="entity_discovery",
            prompt=content,
            user_id=user_context.user_id
        )
```

**Directory Structure:**
```
shared/llm_service/
├── router.py          # Main LLMRouter with fallback chain
├── providers/         # OpenRouter, Anthropic, OpenAI, Google integrations
├── models.py          # Task-specific model mappings
├── credits.py         # Credit estimation and tracking
├── config.py          # Simple configuration management
└── exceptions.py      # Provider failure handling
```

**Alternatives Considered:**
- **Per-Block Integration**: Simple but leads to code duplication and inconsistent error handling
- **Single Provider**: Reduces complexity but creates vendor lock-in and reliability risks
- **Complex Model Selection**: ML-based routing adds unnecessary complexity for current needs
- **Detailed Cost Estimation**: Perfect accuracy not needed initially, crude estimation with future upgrade path better

**Consequences:**
- ✅ **Benefits**: Consistent LLM behavior across all blocks, reduced vendor risk, centralized credit tracking
- ✅ **Benefits**: High availability through multi-provider fallbacks, efficient error recovery
- ✅ **Benefits**: Simple block integration pattern, maintainable configuration management
- ✅ **Benefits**: Future-ready architecture for sophisticated cost optimization and model selection
- ⚠️ **Drawbacks**: Additional complexity before Block 1 implementation
- ⚠️ **Drawbacks**: Multiple API keys and provider management overhead
- ⚠️ **Drawbacks**: Crude credit estimation may not reflect actual costs precisely

**Related ADRs:** ADR-0005 (AI Model Strategy), ADR-0010 (Credit-Based Architecture), ADR-0006 (Secrets Management)

---

## Future ADRs (Planned)

### Implementation Phase ADRs (Week 2-8)
- **ADR-0015**: API Design Patterns and Versioning Strategy
- **ADR-0016**: Testing Strategy (Unit, Integration, End-to-End)
- **ADR-0017**: Error Handling and Logging Architecture
- **ADR-0018**: Authentication and Authorization Implementation
- **ADR-0019**: Document Processing Pipeline Design

### Integration Phase ADRs (Week 8-16)
- **ADR-0020**: Inter-Block Communication Protocols
- **ADR-0021**: Message Queue Architecture and Patterns
- **ADR-0022**: Performance Monitoring and Observability
- **ADR-0023**: Container Orchestration and Deployment Strategy
- **ADR-0024**: Data Backup and Recovery Procedures

### Production Phase ADRs (Week 16+)
- **ADR-0025**: CI/CD Pipeline Architecture
- **ADR-0026**: Production Monitoring and Alerting
- **ADR-0027**: Disaster Recovery and Business Continuity
- **ADR-0028**: Cost Optimization and Resource Management
- **ADR-0029**: Security Audit and Compliance Framework

---

## ADR Change Log

| Date | ADR | Change | Reason |
|------|-----|--------|---------|
| 2025-09-07 | ADR-0001 to ADR-0008 | Initial architectural decisions documented | Establish baseline architecture decisions before implementation begins |
| 2025-09-07 | ADR-0003 | Updated from "Entity Discovery First" to "Block 0 Document Pre-processing First" | Indian market document quality challenges require preprocessing foundation |
| 2025-09-07 | ADR-0009 to ADR-0012 | Added critical architectural decisions from PRD deep-dive | Capture business model, quality strategy, and market-specific decisions |

---

## How to Add New ADRs

1. **Create New ADR**: Add new section with next sequential number
2. **Use Template**: Follow the standard ADR template format
3. **Link Related ADRs**: Reference related decisions for context
4. **Update Change Log**: Document when and why ADR was added/modified
5. **Team Review**: Discuss significant ADRs before marking as "Accepted"

**ADR Statuses:**
- **Proposed**: Under discussion, not yet decided
- **Accepted**: Decision made and being implemented
- **Deprecated**: No longer relevant but kept for historical context
- **Superseded**: Replaced by newer ADR (reference the replacement)

This ADR file will grow as FirstDraft v2.0 evolves from architecture phase through implementation to production deployment.