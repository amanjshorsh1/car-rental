// Live price quote on the booking form (the price comes from the Python model).
(function () {
  const start = document.getElementById("start");
  const end = document.getElementById("end");
  const box = document.getElementById("quote");
  if (!start || !end || !box) return;

  // A date is only "complete" once the year has 4 digits (2000+). While the user is
  // still typing the year the browser reports values like 0002-11-05, which we ignore.
  const complete = (v) => v && Number(v.slice(0, 4)) >= 2000;
  let timer = null;

  async function refresh() {
    box.classList.remove("bad", "good");
    if (!complete(start.value) || !complete(end.value)) {
      box.textContent = box.dataset.hint;
      return;
    }
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

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(refresh, 350);       // wait until typing has settled
  }

  // The return date can't be before pick-up. Only update `min` when the PICK-UP date
  // changes: touching it while the return date is being typed resets the year field.
  start.addEventListener("change", () => {
    if (complete(start.value)) end.min = start.value;
    schedule();
  });
  end.addEventListener("change", schedule);
  refresh();
})();
