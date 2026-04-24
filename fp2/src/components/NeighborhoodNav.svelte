<script>
  import { FEATURED, currentIndex, currentNeighborhood, nextNeighborhood, prevNeighborhood, goToNeighborhood } from '../stores/navigation.js';
</script>

<nav class="neighborhood-nav">
  <div class="nav-main">
    <button class="nav-arrow" on:click={prevNeighborhood} aria-label="Previous neighborhood">
      <svg width="20" height="20" viewBox="0 0 20 20"><path d="M13 4l-6 6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    </button>

    <div class="nav-center">
      <h1 class="nav-hood-name">{$currentNeighborhood}</h1>
      <div class="nav-dots">
        {#each FEATURED as hood, i}
          <button
            class="nav-dot"
            class:active={i === $currentIndex}
            on:click={() => goToNeighborhood(hood)}
            aria-label={hood}
            title={hood}
          ></button>
        {/each}
      </div>
    </div>

    <button class="nav-arrow" on:click={nextNeighborhood} aria-label="Next neighborhood">
      <svg width="20" height="20" viewBox="0 0 20 20"><path d="M7 4l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    </button>
  </div>

</nav>

<style>
  .neighborhood-nav {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.97);
    border-bottom: 1px solid #e0e0e0;
    position: sticky;
    top: 0;
    z-index: 20;
  }

  .nav-main {
    display: flex;
    align-items: center;
    gap: 16px;
    width: 100%;
    justify-content: center;
  }

  .nav-arrow {
    background: none;
    border: 1px solid #ddd;
    border-radius: 50%;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: #666;
    transition: all 0.15s;
    flex-shrink: 0;
  }
  .nav-arrow:hover { border-color: #2d8c2d; color: #2d8c2d; }

  .nav-center { text-align: center; }

  .nav-hood-name {
    font-size: 1.3rem;
    font-weight: 700;
    color: #1a1a1a;
    letter-spacing: -0.01em;
    margin-bottom: 6px;
  }

  .nav-dots {
    display: flex;
    gap: 6px;
    justify-content: center;
  }

  .nav-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: none;
    background: #ddd;
    cursor: pointer;
    padding: 0;
    transition: background 0.15s;
  }
  .nav-dot.active { background: #2d8c2d; }
  .nav-dot:hover { background: #999; }

</style>
