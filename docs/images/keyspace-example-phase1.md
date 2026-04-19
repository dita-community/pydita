# Key Space Construction Example — Phase 1: Populate

Each scope contains only the key definitions declared directly within it.
The map tree on the right is the source; the key spaces on the left reflect what has been collected so far.

```mermaid
flowchart LR
    subgraph KS["Key Spaces (after Phase 1)"]
        direction TB
        subgraph ROOT["Root Scope (anonymous)"]
            R_logo["logo: corp-logo.png"]
        end
        subgraph PROD["Scope: product"]
            P_logo["logo: prod-logo.png"]
            P_title["title: prod-title.dita"]
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

    Mrootkey -.->|defines| R_logo
    MPK1 -.->|defines| P_logo
    MPK2 -.->|defines| P_title
    MWK -.->|defines| W_icon

    classDef local fill:#d4edda,stroke:#28a745,color:#155724
    classDef scoperef fill:#cce5ff,stroke:#004085,color:#004085
    classDef keydef fill:#e2e3e5,stroke:#6c757d,color:#383d41
    classDef maproot fill:#dee2e6,stroke:#495057,color:#212529

    class R_logo,P_logo,P_title,W_icon local
    class Mprod,Mwidg scoperef
    class Mrootkey,MPK1,MPK2,MWK keydef
    class Mroot maproot
```

**Legend**

| Color | Meaning |
|-------|---------|
| Green | Locally defined key (declared directly in this scope) |
| Blue node | Scope-creating topicref (`keyscope` attribute) |
| Gray node | Key-defining element (`keys` attribute) |

After Phase 1, each scope sees **only its own directly declared keys**.
`product` has its own `logo` — but so does the root. That conflict is not yet resolved.
`widget`'s `icon` is invisible to `product` and root until Phase 2.
