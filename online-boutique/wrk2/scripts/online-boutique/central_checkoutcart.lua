local socket = require("socket")
math.randomseed(socket.gettime()*1000)
math.random(); math.random(); math.random()

local url = "http://node2.gangmuk-184284.istio-pg0.clemson.cloudlab.us:32340"

local function addtocart()
  local method = "POST"
  local path = url .. "/cart/checkout?email=fo%40bar.com&street_address=405&zip_code=945&city=Fremont&state=CA&country=USA&credit_card_number=5555555555554444&credit_card_expiration_month=12&credit_card_expiration_year=2025&credit_card_cvv=222"

  local headers = {}
  headers["x-slate-destination"] = "central"
  return wrk.format(method, path, headers, nil)
end

request = function()
  return addtocart(url)
end
