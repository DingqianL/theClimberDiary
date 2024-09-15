async function initialize () {
  const options = {'method': 'GET', 'headers': {'value': '3'}}
  const response = await fetch('https://app.dingqianliu.com/ping', options)
  const data = await response.json()
  document.querySelector('#my-value').textContent = data
}

document.addEventListener('DOMContentLoaded', function() {
  initialize()
}, false);
