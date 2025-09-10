# FirstDraft v2.0 Legal AI Platform - Product Requirements Document

## 1. Executive Summary

FirstDraft v2.0 is an enterprise-grade modular legal AI platform that replaces paralegal grunt work, not experienced lawyers. The platform focuses on perfecting foundational data extraction (client identity, case background, document inventory, timeline of events) before advancing to insights and advisory features. Built for the Indian legal market with robust document quality handling.

**Core Value Proposition**: "AI Paralegal" - automate time-consuming document processing tasks that currently require paralegals and rookie lawyers, empowering experienced lawyers with clean, reliable foundational data.

## 2. Product Vision & Strategy

### Vision Statement
Automated litigation document discovery with entity-aware processing that lawyers trust.

### Mission Statement  
Help lawyers quickly understand clients, cases, and documents through AI-driven extraction and classification, focusing on data accuracy over legal advice.

### Strategic Positioning
- **Replace**: Paralegal document organization, entity cataloging, timeline construction, fact extraction
- **Empower**: Experienced lawyers with reliable foundational data
- **Avoid**: Legal advice, privilege determinations, case strategy, jurisdiction-specific recommendations

### Key Differentiators
- Foundation-first approach: Perfect data quality before attempting insights
- Indian market optimization: Handles poor document quality gracefully
- Modular architecture: Each block could become standalone product
- Credit-based transparency: Users control cost vs. accuracy tradeoffs

## 3. Target Market & Users

### Primary User (Customer Zero)
- **Profile**: Experienced lawyer (20+ years) with litigation practice
- **Pain Points**: Time spent on paralegal tasks, poor document quality from clients, manual entity disambiguation
- **Success Metrics**: Time savings on foundational case setup, trust in AI outputs

### Secondary Users (Alpha Testing)
- **Profile**: Legal team members (partners, associates, paralegals)
- **Use Case**: Free usage for feedback and refinement
- **Value**: Faster case preparation, consistent document processing

### Market Context
- **Geography**: India-first design
- **Document Quality**: Mixed quality inputs (photos, scanned documents, poor OCR)
- **Client Base**: Diverse education/income levels affecting document quality
- **Compliance**: Attorney-client privilege protection essential

## 4. Business Model

### Credit-Based System
- **Core Model**: Users purchase credits for AI processing
- **Transparency**: Upfront burn rate estimates before processing
- **User Control**: Simple override options for cost/quality tradeoffs

### Pricing Approach (Indicative)
- **Default**: FirstDraft recommends optimal models for each task
- **Override Option**: "Use budget models instead" with revised cost estimate
- **Display**: "Recommended: 150 credits ($15) - Premium models for accuracy"
- **Alternative**: "Budget option: 80 credits ($8) - Lower accuracy but cost-effective"

### Revenue Streams (Post-MVP)
- Each block could become standalone product (Entity Intelligence, Timeline Builder, etc.)
- Enterprise licensing for law firms
- API access for legal tech integrations

## 5. Product Architecture

### Modular "Lego Blocks" Design
Each block is designed for standalone potential while integrating seamlessly:

**Block 0: Document Pre-processing (NEW - Foundational)**
- OCR and format standardization
- Quality assessment and warnings
- Image enhancement and rotation correction
- Multi-language support (Hindi/English)
- Never reject documents, always warn about quality impact

**Block 1: Entity Discovery Engine**  
- Confidence-based entity extraction (95%+ auto-confirm)
- Context-driven disambiguation using case details
- Multi-party legal relationship mapping
- Corporate hierarchy identification
- Flag conflicts with best guess answers

**Block 2: Content Storage Engine**
- Content-addressable storage with deduplication
- Extensible schema for iterative enhancement
- Document version management
- Integration-ready outputs for downstream blocks

**Block 3: AI Processing Engine**
- Multi-model AI cascade (premium → cost-effective)
- Lawyer-friendly document classification
- Core value extraction in third person
- Model routing: OpenRouter primary, direct APIs as fallback

**Block 4: Queue Management Engine**
- Enterprise job orchestration
- Processing status tracking
- Credit usage monitoring

**Block 5: Multi-Tenant Management**  
- Basic user management for future client isolation
- Tenant-specific configurations
- Usage tracking and billing support

**Block 6: API Gateway Engine**
- External interface and routing
- Authentication and rate limiting
- Credit management and billing integration

## 6. Core Features & MVP Scope

### MVP Includes (Foundation Data Layer)
1. **Document Organization**: Sort and categorize uploaded files
2. **Entity Cataloging**: Complete list of people and companies mentioned
3. **Timeline Construction**: Chronological sequence of events  
4. **Key Document Identification**: Contracts, correspondence, invoices classification
5. **Basic Fact Extraction**: Key dates, amounts, and claims
6. **Conflict Resolution**: Flag discrepancies with best guess resolution

### MVP Excludes (Explicitly)
- Legal advice or recommendations
- Privilege determinations  
- Case strategy suggestions
- Document quality scoring
- Opposing counsel analysis
- Jurisdiction-specific legal guidance
- Advanced analytics (post-MVP feature)

### Document Scope
**Included in MVP:**
- Text-based: Word docs, PDFs with selectable text
- OCR required: Scanned documents, images of documents
- Legal formats: Court filings, discovery responses, contracts
- Mixed quality: Photos, handwritten notes (with quality warnings)

**Excluded from MVP:**
- Spreadsheets, audio files, video files
- Complex multimedia processing

## 7. User Experience & Workflow

### Case Input Process
**Structured Fields + Free-form Narrative:**
- Client name, opposing party, case type (dropdown)
- Key dates, dispute summary
- Free-form context area for additional details

### Document Upload & Processing  
1. **Upload**: Drag-and-drop interface for multiple file types
2. **Quality Assessment**: Block 0 analyzes and warns about poor quality docs
3. **Cost Estimation**: "Recommended: 150 credits ($15) - Premium models for accuracy"
4. **User Choice**: Accept recommendation or "Use budget models" option
5. **Processing**: Status updates with credit consumption tracking
6. **Output**: Markdown file with organized results

### Output Format
**Markdown Report Structure:**
- Executive summary of case entities and timeline
- Complete entity list with confidence scores
- Document inventory with dates and classifications  
- Timeline of key events with source document references
- Flagged conflicts requiring lawyer review
- Quality warnings for specific documents

## 8. Success Metrics & Validation

### Primary Success Metrics
- **Accuracy**: 90%+ entity identification accuracy
- **Time Savings**: Process in 10 minutes what takes paralegal 2 hours
- **Trust Level**: Lawyer confident enough to use in actual case prep
- **Edge Case Handling**: Graceful handling of poor quality documents

### User Validation Strategy
1. **Customer Zero Testing**: 20+ years legal experience provides validation
2. **Real World Testing**: Use actual case files (anonymized/controlled risk)  
3. **Team Alpha Testing**: Free usage by legal team for feedback
4. **Quality Benchmarking**: Compare against manual paralegal work

### Business Validation
- User adoption and retention rates
- Credit usage patterns and revenue per user
- Feature usage analytics (which blocks provide most value)
- Customer satisfaction and referral rates

## 9. Technical Requirements

### AI Model Strategy
**Premium Models**: Complex entity discovery, legal reasoning, multi-party relationships
- Claude-3.5-Sonnet, GPT-4o for sophisticated analysis

**Cost-Effective Models**: Text classification, simple extraction, summarization
- DeepSeek, Together AI for high-volume simple tasks

**AI Provider Architecture**:
- Primary: OpenRouter (unified API, model flexibility)
- Direct Integration: Anthropic, OpenAI for premium models  
- Fallback: Multiple provider redundancy for reliability

### Technology Stack
- **API Framework**: FastAPI (async, high performance)
- **Database**: PostgreSQL (multi-tenant, extensible schema)
- **Message Queue**: Redis/Celery (job processing)
- **Storage**: S3/MinIO (content-addressable)
- **Package Manager**: UV (10x faster than pip)
- **Containerization**: Docker + Kubernetes ready

### Database Strategy
**Extensible Schema Design:**
- Placeholder columns for future features (rotation_corrected, language_detected)
- Metadata fields for processing pipeline extensibility
- Multi-version document storage support
- Migration-ready architecture with Alembic

## 10. Development Strategy & Timeline

### Approach
- **Block-by-Block Development**: Perfect each block before moving to next
- **Quality-First**: Extensive testing at each stage
- **Real-World Validation**: Test with actual legal documents
- **Modular Architecture**: Each block designed for potential standalone use

### Implementation Sequence
**Phase 1: Block 0a (Document Pre-processing)**
- Duration: 4-5 weeks
- Scope: OCR + format standardization + quality warnings + extensible schema
- Testing: Real-world document processing with controlled risk data

**Phase 2: Block 1 (Entity Discovery)**  
- Duration: 5-6 weeks
- Scope: Confidence-based extraction + disambiguation + integration with Block 0a
- Testing: Legal document corpus with entity accuracy benchmarking

**Phase 3: Integration & Refinement**
- Duration: Per block based on learnings
- Approach: Reassess complexity and scope after Block 0a + Block 1 completion

### Development Philosophy
- No time pressure - quality over speed
- Modular hiring strategy post-MVP
- Iterative schema evolution with migration support
- Cross-block integration testing essential

## 11. Risk Management

### Technical Risks & Mitigations
- **Document Quality Issues**: Never reject, always process with warnings
- **AI Model Failures**: Multi-provider cascade with fallback options
- **Integration Complexity**: Extensive testing at each block handoff
- **Database Evolution**: Extensible schema design from day one

### Market Risks & Mitigations  
- **User Adoption**: Customer zero validation + legal team alpha testing
- **Accuracy Expectations**: Clear foundation-first positioning, avoid over-promising
- **Competition**: Focus on Indian market optimization + modular architecture
- **Pricing Model**: Credit system allows flexible cost/quality positioning

### Operational Risks & Mitigations
- **Client Confidentiality**: Controlled risk testing with anonymized real documents
- **Scalability**: Modular architecture allows independent block scaling
- **Regulatory Compliance**: Attorney-client privilege protection built-in
- **Cost Control**: Transparent credit system with user override options

## 12. Stakeholders & Governance

### Primary Stakeholder
- **Role**: Solo entrepreneur with 20+ years legal experience
- **Responsibilities**: Product vision, customer zero testing, final approval
- **Success Criteria**: Would use in own legal practice confidently

### Development Team
- **Current**: Solo development with AI assistance
- **Future**: Hire developers for productionalization post-MVP
- **Approach**: Modular blocks enable distributed development

### Alpha Testing Group
- **Composition**: Legal team members (partners, associates, paralegals)
- **Engagement**: Free usage in exchange for detailed feedback
- **Timeline**: Post-Block 1 completion for meaningful testing

## 13. Success Criteria & Next Steps

### MVP Success Definition
Block 0a + Block 1 successfully demonstrate:
- Reliable document processing with quality warnings
- Accurate entity discovery with confidence scoring  
- Clean data handoff between blocks
- Lawyer-level trust in foundational outputs
- Clear path to Block 2 integration

### Decision Points
After Block 0a + Block 1 completion:
- Validate architectural assumptions
- Reassess remaining block complexity
- Adjust timeline and resource allocation
- Plan team expansion strategy

### Long-term Vision
- Each block becomes potential standalone product
- Platform approach with API ecosystem
- Enterprise law firm adoption
- Geographic expansion beyond India

---

**Document Status**: Finalized for implementation  
**Last Updated**: 2025-09-07  
**Next Review**: Post-Block 0a completion