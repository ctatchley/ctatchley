const recipeGrid = document.querySelector("#recipeGrid");
const recipeTemplate = document.querySelector("#recipeTemplate");
const recipeForm = document.querySelector("#recipeForm");
const filterForm = document.querySelector("#filterForm");
const searchInput = document.querySelector("#searchInput");
const categoryFilter = document.querySelector("#categoryFilter");
const categorySelect = document.querySelector("#categorySelect");
const recipeCount = document.querySelector("#recipeCount");
const formMessage = document.querySelector("#formMessage");

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Something went wrong.");
  }
  return payload;
}

function ratingText(recipe) {
  if (!recipe.rating_count) {
    return "No ratings";
  }
  const label = recipe.rating_count === 1 ? "rating" : "ratings";
  return `${recipe.rating_average} / 5 (${recipe.rating_count} ${label})`;
}

function renderRecipes(recipes) {
  if (!recipeGrid || !recipeCount) {
    return;
  }

  recipeGrid.innerHTML = "";
  recipeCount.textContent = `${recipes.length} ${recipes.length === 1 ? "recipe" : "recipes"}`;

  if (!recipes.length) {
    recipeGrid.innerHTML = '<p class="empty-state">No recipes yet. Share the first one from the share page.</p>';
    return;
  }

  recipes.forEach((recipe) => {
    const card = recipeTemplate.content.firstElementChild.cloneNode(true);
    const image = card.querySelector(".recipe-image");
    const ratingForm = card.querySelector(".rating-form");

    card.querySelector("h3").textContent = recipe.title;
    card.querySelector(".category").textContent = formatCategory(recipe.category);
    card.querySelector(".rating").textContent = ratingText(recipe);
    card.querySelector(".ingredients").textContent = recipe.ingredients;
    card.querySelector(".instructions").textContent = recipe.instructions;

    if (recipe.image_url) {
      image.src = recipe.image_url;
      image.alt = recipe.title;
    } else {
      image.hidden = true;
    }

    ratingForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(ratingForm);
      await fetchJson(`/api/recipes/${recipe.id}/ratings`, {
        method: "POST",
        body: formData,
      });
      await loadRecipes();
    });

    recipeGrid.append(card);
  });
}

async function loadCategories() {
  const categories = await fetchJson("/api/categories");

  if (categoryFilter) {
    const selected = categoryFilter.value;
    categoryFilter.innerHTML = '<option value="">All categories</option>';
    appendCategoryOptions(categoryFilter, categories);
    categoryFilter.value = selected;
  }

  if (categorySelect) {
    const selected = categorySelect.value;
    categorySelect.innerHTML = '<option value="">Choose a category</option>';
    appendCategoryOptions(categorySelect, categories);
    categorySelect.value = selected;
  }
}

function appendCategoryOptions(select, categories) {
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = formatCategory(category);
    select.append(option);
  });
}

function formatCategory(category) {
  return category.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function loadRecipes() {
  if (!recipeGrid || !categoryFilter || !searchInput) {
    return;
  }

  const params = new URLSearchParams();
  if (categoryFilter.value) {
    params.set("category", categoryFilter.value);
  }
  if (searchInput.value.trim()) {
    params.set("search", searchInput.value.trim());
  }

  const query = params.toString();
  const recipes = await fetchJson(`/api/recipes${query ? `?${query}` : ""}`);
  renderRecipes(recipes);
}

if (recipeForm) {
  recipeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    formMessage.textContent = "Posting recipe...";

    try {
      await fetchJson("/api/recipes", {
        method: "POST",
        body: new FormData(recipeForm),
      });
      recipeForm.reset();
      formMessage.innerHTML = 'Recipe posted. <a href="/">View recipes</a>';
    } catch (error) {
      formMessage.textContent = error.message;
    }
  });
}

if (filterForm) {
  filterForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await loadRecipes();
  });
}

if (categoryFilter) {
  categoryFilter.addEventListener("change", loadRecipes);
}

loadCategories()
  .then(loadRecipes)
  .catch((error) => {
    if (recipeGrid) {
      recipeGrid.innerHTML = `<p class="empty-state">${error.message}</p>`;
    } else if (formMessage) {
      formMessage.textContent = error.message;
    }
  });
