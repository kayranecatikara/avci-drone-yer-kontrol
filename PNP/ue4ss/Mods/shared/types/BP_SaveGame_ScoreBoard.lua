---@meta

---@class UBP_SaveGame_ScoreBoard_C : USaveGame
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ScoreboardPole FS_Scoreboard
---@field ScoreboardRuinedCity FS_Scoreboard
---@field ScoreboardRural FS_Scoreboard
---@field ScoreboardMilitaryAirport FS_Scoreboard
---@field ScoreboardPeak FS_Scoreboard
---@field ScoreboardJungle FS_Scoreboard
---@field ScoreboardTrench FS_Scoreboard
---@field TotalTime double
---@field TotalFlyTime double
---@field TotalKillCount int32
local UBP_SaveGame_ScoreBoard_C = {}

---@param Level E_Levels::Type
---@return FS_Scoreboard
function UBP_SaveGame_ScoreBoard_C:GetScoreboard(Level) end
---@param Level E_Levels::Type
---@param FailCrashCount int32
---@param SuccessCrashCount int32
---@param TotalTime FString
function UBP_SaveGame_ScoreBoard_C:SaveScorebaordData(Level, FailCrashCount, SuccessCrashCount, TotalTime) end
---@param EntryPoint int32
function UBP_SaveGame_ScoreBoard_C:ExecuteUbergraph_BP_SaveGame_ScoreBoard(EntryPoint) end


