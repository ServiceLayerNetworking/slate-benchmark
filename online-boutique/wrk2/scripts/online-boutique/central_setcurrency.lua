local socket = require("socket")
math.randomseed(socket.gettime()*1000)
math.random(); math.random(); math.random()

local url = "http://node2.gangmuk-184284.istio-pg0.clemson.cloudlab.us:32340"

local function addtocart()
  local method = "POST"
  local path = url .. "/setCurrency?currency_code=EUR"

  local headers = {}
  headers["x-slate-destination"] = "central"
  return wrk.format(method, path, headers, nil)
end

request = function()
  return addtocart(url)
end