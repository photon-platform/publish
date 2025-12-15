Color Swatches
==============

This page demonstrates the color palette variables.

.. raw:: html

    <style>
        .swatch-container {
            display: flex;
            flex-wrap: wrap;
            gap: 1em;
        }
        .swatch {
            width: 150px;
            height: 100px;
            border: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            border-radius: 8px;
            color: var(--text-color);
            text-shadow: 0 1px 2px black;
        }
        .swatch span {
            background: rgba(0,0,0,0.5);
            padding: 2px 5px;
            border-radius: 4px;
        }
    </style>

    <div class="swatch-container">
        <div class="swatch" style="background-color: var(--bg-color);"><span>--bg-color</span></div>
        <div class="swatch" style="background-color: var(--bg-alt-color);"><span>--bg-alt-color</span></div>
        <div class="swatch" style="background-color: var(--text-color); color: black;"><span>--text-color</span></div>
        <div class="swatch" style="background-color: var(--heading-color); color: black;"><span>--heading-color</span></div>
        <div class="swatch" style="background-color: var(--link-color);"><span>--link-color</span></div>
        <div class="swatch" style="background-color: var(--link-hover-color);"><span>--link-hover-color</span></div>
        <div class="swatch" style="background-color: var(--border-color);"><span>--border-color</span></div>
        
        <!-- Semantic Colors -->
        <div class="swatch" style="background-color: var(--color-success);"><span>--color-success</span></div>
        <div class="swatch" style="background-color: var(--color-warning);"><span>--color-warning</span></div>
        <div class="swatch" style="background-color: var(--color-danger);"><span>--color-danger</span></div>
        <div class="swatch" style="background-color: var(--color-info);"><span>--color-info</span></div>
        <div class="swatch" style="background-color: var(--color-note);"><span>--color-note</span></div>
        <div class="swatch" style="background-color: var(--color-muted);"><span>--color-muted</span></div>
        <div class="swatch" style="background-color: var(--color-property);"><span>--color-property</span></div>
        
        <!-- Social Colors -->
        <div class="swatch" style="background-color: var(--facebook-color);"><span>Facebook</span></div>
        <div class="swatch" style="background-color: var(--twitter-color);"><span>Twitter</span></div>
        <div class="swatch" style="background-color: var(--github-color);"><span>GitHub</span></div>
    </div>
