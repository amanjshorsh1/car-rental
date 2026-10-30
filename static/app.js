// Live price quote on the booking form (the price comes from the Python model).
(function () {
  const start = document.getElementById("start");
  const end = document.getElementById("end");
  const box = document.getElementById("quote");
  if (!start || !end || !box) return;

  async function refresh() {
    box.classList.remove("bad", "good");
    if (!start.value || !end.value) { box.textContent = box.dataset.hint; return; }
    if (start.value) end.min = start.value;
    try {
      const url = `${box.dataset.url}?car_id=${box.dataset.car}&start=${start.value}&end=${end.value}`;
      const data = await (await fetch(url)).json();
      if (data.ok) {
        box.classList.add("good");
        box.textContent = `${box.dataset.days}: ${data.days} · ${box.dataset.total}: $${data.total}`;
      } else {
        box.classList.add("bad");
        box.textContent = data.message;
      }
    } catch (e) {
      box.textContent = box.dataset.hint;
    }
  }
  start.addEventListener("change", refresh);
  end.addEventListener("change", refresh);
  refresh();
})();
