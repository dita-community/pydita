# Key Space Construction Example — Phase 2: Pull Up

`PullUpVisitor` walks post-order (leaves first). Each scope qualifies its key names with its own scope name and passes them up to its parent's collector. After a parent finishes visiting all children, it adds the collected aliases to itself, then re-qualifies the full set before passing further up.

```mermaid
flowchart LR
    subgraph KS["Key Spaces (after Phase 2)"]
        direction TB
        subgraph ROOT["Root Scope (anonymous)"]
            R_logo["logo: corp-logo.png"]
            R_PL["product.logo: prod-logo.png"]
            R_PT["product.title: prod-title.dita"]
            R_PWI["product.widget.icon: widget-icon.png"]
        end
        subgraph PROD["Scope: product"]
            P_logo["logo: prod-logo.png"]
            P_title["title: prod-title.dita"]
            P_WI["widget.icon: widget-icon.png"]
        end
        subgraph WIDG["Scope: widget"]
            W_icon["icon: widget-icon.png"]
        end
    end

    subgraph MAP["DITA Map Tree"]
        direction TB
        Mroot(["Root Map"])
        Mrootkey["keydef\nkeys=logo\nhref=corp-logo.png"]
        Mprod["topicref\nkeyscope=product"]
        MPK1["keydef\nkeys=logo\nhref=prod-logo.png"]
        MPK2["keydef\nkeys=title\nhref=prod-title.dita"]
        Mwidg["topicref\nkeyscope=widget"]
        MWK["keydef\nkeys=icon\nhref=widget-icon.png"]

        Mroot --> Mrootkey
        Mroot --> Mprod
        Mprod --> MPK1
        Mprod --> MPK2
        Mprod --> Mwidg
        Mwidg --> MWK
    end

    WIDG -->|"1. widget qualifies icon as widget.icon,\npasses to product collector"| PROD
    PROD -->|"2. product adds widget.icon, then qualifies\nall keys as product.*,\npasses to root collector"| ROOT

    classDef local fill:#d4edda,stroke:#28a745,color:#155724
    classDef pullup fill:#cce5ff,stroke:#004085,color:#004085
    classDef scoperef fill:#fff3cd,stroke:#856404,color:#533f03
    classDef keydef fill:#e2e3e5,stroke:#6c757d,color:#383d41
    classDef maproot fill:#dee2e6,stroke:#495057,color:#212529

    class R_logo,P_logo,P_title,W_icon local
    class R_PL,R_PT,R_PWI,P_WI pullup
    class Mprod,Mwidg scoperef
    class Mrootkey,MPK1,MPK2,MWK keydef
    class Mroot maproot
```

**What changed from Phase 1**

| Scope | New entries added by pull-up |
|-------|------------------------------|
| `product` | `widget.icon: widget-icon.png` (from widget, step 1) |
| Root | `product.logo`, `product.title`, `product.widget.icon` (from product, step 2) |
| `widget` | — (leaf scope, nothing to receive) |

**Legend**

| Color | Meaning |
|-------|---------|
| Green | Locally defined key (from Phase 1) |
| Blue | Qualified alias added by pull-up (this phase) |

After Phase 2, the root can resolve `product.widget.icon` even though `icon` was declared two levels down.
The `logo` conflict is still unresolved — both root and `product` have their own local `logo` definition.
That is resolved in Phase 3.
