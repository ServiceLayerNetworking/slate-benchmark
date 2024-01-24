local socket = require("socket")
math.randomseed(socket.gettime()*1000)
math.random(); math.random(); math.random()

local url = "http://node2.gangmuk-184284.istio-pg0.clemson.cloudlab.us:32340"

-- light weight matmul
local function get()
  local method = "GET"
  local row = "2"
  local column = "2"
  local path = url .. "/compute?row=" .. row .. "&column=" .. column
  local headers = {}
  headers["x-slate-destination"] = "west"
  -- headers["Content-Type"] = "application/x-www-form-urlencoded"
  return wrk.format(method, path, headers, nil)
end


request = function()
  return get(url)
end
