# Adds a WidgetKit extension target to a Flutter iOS project, without the Xcode GUI.
# Run with the Ruby that has the xcodeproj gem (CocoaPods ships it), from the ios/ folder:
#   GEM_HOME=<cocoapods libexec> <cocoapods ruby> add_widget_target.rb Runner.xcodeproj <Name> <bundle.id.of.app> <TEAM_ID>
# Expects ios/<Name>/<Name>.swift, Info.plist (NSExtensionPointIdentifier = com.apple.widgetkit-extension)
# and <Name>.entitlements (the App Group). Safe to run once; it aborts if the target exists.
require 'xcodeproj'
proj_path, name, app_id, team = ARGV
project = Xcodeproj::Project.open(proj_path)
abort("#{name} already exists") if project.targets.any? { |t| t.name == name }
runner = project.targets.find { |t| t.name == 'Runner' }

widget = project.new_target(:app_extension, name, :ios, '15.0', nil, :swift)
group = project.main_group.new_group(name, name)
swift = group.new_file("#{name}.swift")
group.new_file('Info.plist')
group.new_file("#{name}.entitlements")
xcconfig = group.new_file("#{name}.xcconfig")
widget.add_file_references([swift])
%w[WidgetKit SwiftUI].each do |fw|
  ref = project.frameworks_group.new_file("System/Library/Frameworks/#{fw}.framework", :sdk_root)
  widget.frameworks_build_phase.add_file_reference(ref, true)
end

widget.build_configurations.each do |c|
  # Own xcconfig: only Flutter's version numbers. Runner's configs pull in the Pods settings.
  c.base_configuration_reference = xcconfig
  s = c.build_settings
  s['PRODUCT_NAME'] = '$(TARGET_NAME)' # empty name gives "Multiple commands produce .../.appex"
  s['PRODUCT_BUNDLE_IDENTIFIER'] = "#{app_id}.#{name}"
  s['INFOPLIST_FILE'] = "#{name}/Info.plist"
  s['GENERATE_INFOPLIST_FILE'] = 'NO'
  s['CODE_SIGN_ENTITLEMENTS'] = "#{name}/#{name}.entitlements"
  s['CODE_SIGN_STYLE'] = 'Automatic'
  s['DEVELOPMENT_TEAM'] = team
  s['SWIFT_VERSION'] = '5.0'
  s['TARGETED_DEVICE_FAMILY'] = '1,2'
  s['SKIP_INSTALL'] = 'YES'
  s['APPLICATION_EXTENSION_API_ONLY'] = 'YES'
  s['LD_RUNPATH_SEARCH_PATHS'] = ['$(inherited)', '@executable_path/Frameworks', '@executable_path/../../Frameworks']
  s['MARKETING_VERSION'] = '$(FLUTTER_BUILD_NAME)'
  s['CURRENT_PROJECT_VERSION'] = '$(FLUTTER_BUILD_NUMBER)'
end
File.write(File.join(File.dirname(proj_path), name, "#{name}.xcconfig"),
           "#include? \"../Flutter/Generated.xcconfig\"\n")

# The app needs the same App Group.
runner.build_configurations.each { |c| c.build_settings['CODE_SIGN_ENTITLEMENTS'] ||= 'Runner/Runner.entitlements' }

# Embed before Flutter's "Thin Binary" phase, or the build fails with "Cycle inside Runner".
embed = runner.new_copy_files_build_phase('Embed Foundation Extensions')
embed.symbol_dst_subfolder_spec = :plug_ins
embed.add_file_reference(widget.product_reference, true).settings = { 'ATTRIBUTES' => ['RemoveHeadersOnCopy'] }
runner.add_dependency(widget)
runner.build_phases.delete(embed)
idx = runner.build_phases.index { |p| p.display_name == 'Thin Binary' } || runner.build_phases.length
runner.build_phases.insert(idx, embed)

project.save
puts "Added #{name}. Runner phases: #{runner.build_phases.map(&:display_name).join(', ')}"
